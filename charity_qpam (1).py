"""
╔══════════════════════════════════════════════════════════════════╗
║          C-QPAM: Charity Quantitative Portfolio Allocation       ║
║          Adapted from QPAM framework by Axiom Capital Research   ║
╚══════════════════════════════════════════════════════════════════╝

Run in Jupyter Notebook for full visual output.
Install: pip install pandas numpy matplotlib
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import warnings
warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────
#  DESIGN SYSTEM
# ─────────────────────────────────────────────
P = {
    'bg':        '#F8F5F0',
    'card':      '#FFFFFF',
    'border':    '#E8E2D9',
    'primary':   '#B71C1C',
    'primary_lt':'#FFEBEE',
    'dark':      '#1A2332',
    'mid':       '#4A5568',
    'muted':     '#94A3B8',
    'positive':  '#1B6B3A',
    'pos_lt':    '#D4EDDA',
    'negative':  '#C0392B',
    'neg_lt':    '#FDECEA',
    'amber':     '#D97706',
    'amber_lt':  '#FEF3C7',
    'grid':      '#EDF2F7',
}

CAT_COLOURS = [
    '#2E86AB', '#A23B72', '#F18F01', '#C73E1D',
    '#3B1F2B', '#44BBA4', '#E94F37', '#393E41',
]


# ─────────────────────────────────────────────────────
#   CharityQPAM  CLASS
# ─────────────────────────────────────────────────────

class CharityQPAM:
    """
    Charity Quantitative Portfolio Allocation Model.

    Parameters
    ----------
    weights : dict
        Factor weights summing to 1.0. Keys: 'T', 'D', 'V'.
    total_floor_sqft : float
        Total sellable floor space in square feet.
    weekly_budget : float
        Weekly discretionary operating budget (£).
    weekly_volunteer_hours : float
        Total volunteer hours available per week.
    min_hours_per_cat : float
        Minimum volunteer hours guaranteed to every category,
        regardless of C-QPAM score. Default 2.0.
    """

    def __init__(
        self,
        weights=None,
        total_floor_sqft: float = 1200,
        weekly_budget: float = 800,
        weekly_volunteer_hours: float = 120,
        min_hours_per_cat: float = 2.0,
    ):
        self.weights = weights or {'T': 0.4, 'D': 0.3, 'V': 0.3}
        assert abs(sum(self.weights.values()) - 1.0) < 1e-6, "Weights must sum to 1."
        self.total_floor_sqft       = total_floor_sqft
        self.weekly_budget          = weekly_budget
        self.weekly_volunteer_hours = weekly_volunteer_hours
        self.min_hours_per_cat      = min_hours_per_cat

        self.categories_ = None
        self.scores_      = None
        self.allocations_ = None
        self.factor_df_   = None
        self.raw_data_    = None

    # ──────────────────────────────────────────
    #   FIT
    # ──────────────────────────────────────────

    def fit(self, sales_df, donations_df, expenses_df):
        self.raw_data_ = {
            'sales': sales_df.copy(),
            'donations': donations_df.copy(),
            'expenses': expenses_df.copy(),
        }

        cats = sorted(sales_df['category'].unique())
        self.categories_ = cats
        n = len(cats)

        sales_agg = (
            sales_df.groupby('category')
            .agg(total_units_sold=('units_sold', 'sum'),
                 total_revenue=('revenue', 'sum'),
                 weeks_active=('week', 'nunique'))
            .reset_index()
        )
        donations_agg = (
            donations_df.groupby('category')
            .agg(total_donated=('units_donated', 'sum'),
                 avg_donated=('units_donated', 'mean'),
                 std_donated=('units_donated', 'std'))
            .reset_index()
        )
        df = sales_agg.merge(donations_agg, on='category')
        df['std_donated'] = df['std_donated'].fillna(0)

        latest_week = donations_df['week'].max()
        latest_don  = (donations_df[donations_df['week'] == latest_week]
                       .set_index('category')['units_donated'])
        df['latest_donated'] = df['category'].map(latest_don).fillna(0)

        # Factor T: Turnover Momentum
        df['sellthrough'] = (df['total_units_sold']
                             / df['total_donated'].replace(0, np.nan)).fillna(0)
        mean_st      = df['sellthrough'].mean()
        df['T_raw']  = df['sellthrough'] / (mean_st if mean_st > 0 else 1)
        df['T']      = self._zscore(df['T_raw'])

        # Factor D: Donation Mean Reversion
        df['D_raw'] = -(df['latest_donated'] - df['avg_donated']) / df['std_donated'].replace(0, 1)
        df['D']     = self._zscore(df['D_raw'])

        # Factor V: Volatility Reliability
        max_std      = df['std_donated'].max()
        df['V_raw']  = 1 - (df['std_donated'] / max_std) if max_std > 0 else 1.0
        df['V']      = self._zscore(df['V_raw'])

        # Composite Score
        w = self.weights
        df['score'] = w['T']*df['T'] + w['D']*df['D'] + w['V']*df['V']

        # Floor & Budget
        df['score_clipped']        = df['score'].clip(lower=0)
        total_pos                  = df['score_clipped'].sum()
        df['floor_allocation_pct'] = (
            df['score_clipped'] / total_pos if total_pos > 0 else 1/n
        )
        df['floor_sqft']        = (df['floor_allocation_pct'] * self.total_floor_sqft).round(0)
        df['budget_allocation'] = (df['floor_allocation_pct'] * self.weekly_budget).round(2)

        # Volunteer Hours with guaranteed minimum floor
        reserve   = self.min_hours_per_cat * n
        flex_pool = max(0, self.weekly_volunteer_hours - reserve)
        t_pos     = df['T'].clip(lower=0)
        t_sum     = t_pos.sum()
        df['volunteer_hours'] = (
            self.min_hours_per_cat
            + (t_pos / t_sum * flex_pool if t_sum > 0 else flex_pool / n)
        ).round(1)

        # Pricing Signal
        df['pricing_signal'] = df.apply(self._pricing_signal, axis=1)

        # Efficiency
        df['rev_per_sqft'] = (df['total_revenue']
                              / df['floor_sqft'].replace(0, np.nan)).round(2)

        self.factor_df_   = df.set_index('category')
        self.scores_      = df.set_index('category')['score']
        self.allocations_ = df.set_index('category')['floor_allocation_pct']
        return self

    # ──────────────────────────────────────────
    #   HELPERS
    # ──────────────────────────────────────────

    @staticmethod
    def _zscore(s):
        std = s.std()
        return (s - s.mean()) / std if std > 0 else pd.Series(0.0, index=s.index)

    @staticmethod
    def _pricing_signal(row):
        sc, st = row['score'], row['sellthrough']
        if   sc >  0.5 and st > 0.80: return '▲ PREMIUM'
        elif sc >  0.0 and st > 0.50: return '= HOLD'
        elif sc <  0.0 and st < 0.40: return '▼ MARKDOWN'
        else:                          return '▼ DISCOUNT'

    # ──────────────────────────────────────────
    #   3-PAGE REPORT
    # ──────────────────────────────────────────

    def report(self, shop_name="C-QPAM Report", save_prefix="cqpam"):
        """Render 3 clean, spacious A4-style pages."""
        df = self.factor_df_.reset_index().sort_values('score', ascending=False)
        self._page1(df, shop_name, save_prefix)
        self._page2(df, shop_name, save_prefix)
        self._page3(df, shop_name, save_prefix)
        print(f"\n✓  {save_prefix}_page1.png")
        print(f"✓  {save_prefix}_page2.png")
        print(f"✓  {save_prefix}_page3.png")

    # ── Shared header helper ───────────────────────────────────────

    def _draw_header(self, fig, shop_name, subtitle, page_label, bg_col, sub_col):
        ax = fig.add_axes([0, 0.938, 1, 0.062])
        ax.set_facecolor(bg_col); ax.axis('off')
        ax.text(0.5, 0.70, shop_name, transform=ax.transAxes,
                fontsize=23, fontweight='bold', color='white', ha='center', va='center')
        ax.text(0.5, 0.18, subtitle, transform=ax.transAxes,
                fontsize=9.5, color=sub_col, ha='center', va='center')
        fig.text(0.97, 0.962, page_label, fontsize=8, color=sub_col, ha='right', va='center')
        fig.text(0.5, 0.010, 'Axiom Capital Research  ·  C-QPAM v1.0  ·  Confidential',
                 ha='center', fontsize=8, color=P['muted'])

    # ── PAGE 1: Executive Overview ─────────────────────────────────

    def _page1(self, df, shop_name, prefix):
        fig = plt.figure(figsize=(16, 20), facecolor=P['bg'])
        self._draw_header(
            fig, shop_name,
            f"C-QPAM v1.0  ·  Axiom Capital Research  ·  "
            f"Weights T={self.weights['T']} / D={self.weights['D']} / V={self.weights['V']}  ·  "
            f"Floor {self.total_floor_sqft:,.0f} sqft  ·  Budget £{self.weekly_budget:,.0f}/wk  ·  "
            f"Volunteers {self.weekly_volunteer_hours} hrs  ·  Min {self.min_hours_per_cat} hrs/cat",
            'PAGE 1 OF 3', P['primary'], '#FFCDD2'
        )

        # ── KPI Cards ────────────────────────────────────────────────
        n_pos   = (df['score'] > 0).sum()
        n_neg   = (df['score'] < 0).sum()
        top_cat = df.iloc[0]['category']
        top_rev = df.sort_values('total_revenue', ascending=False).iloc[0]
        kpis = [
            ('PRIORITY', str(n_pos), 'categories to grow', P['positive'], P['pos_lt'], P['positive']),
            ('REVIEW',   str(n_neg), 'flagged for markdown', P['negative'], P['neg_lt'], P['negative']),
            ('TOP SCORE', top_cat,  'highest C-QPAM score', P['dark'], '#EFF6FF', P['dark']),
            ('TOP REVENUE', top_rev['category'], f"£{top_rev['total_revenue']:,.0f} earned", P['amber'], P['amber_lt'], P['amber']),
        ]
        for i, (title, val, sub, txt, bg, border) in enumerate(kpis):
            ax = fig.add_axes([0.04 + i*0.237, 0.862, 0.215, 0.068])
            ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis('off')
            ax.add_patch(FancyBboxPatch((0.02,0.04), 0.96, 0.92,
                                        boxstyle='round,pad=0.03',
                                        linewidth=2, edgecolor=border,
                                        facecolor=bg, transform=ax.transAxes))
            ax.text(0.5, 0.80, title, transform=ax.transAxes, fontsize=8,
                    color=P['mid'], ha='center', va='center', fontweight='bold')
            ax.text(0.5, 0.44, val, transform=ax.transAxes, fontsize=21,
                    color=txt, ha='center', va='center', fontweight='bold')
            ax.text(0.5, 0.10, sub, transform=ax.transAxes, fontsize=7.5,
                    color=P['muted'], ha='center', va='center')

        # ── Score Bar Chart ───────────────────────────────────────────
        ax_bar = fig.add_axes([0.08, 0.475, 0.86, 0.365])
        ax_bar.set_facecolor(P['card'])
        cats   = df['category'].tolist()
        scores = df['score'].tolist()
        y_pos  = np.arange(len(cats))
        colours = [P['positive'] if s >= 0 else P['negative'] for s in scores]
        bars = ax_bar.barh(y_pos, scores, color=colours, height=0.58,
                           edgecolor='white', linewidth=1.0, zorder=3)
        ax_bar.axvline(0, color=P['dark'], linewidth=1.8, zorder=4, alpha=0.4)
        for bar, val in zip(bars, scores):
            offset = 0.035 if val >= 0 else -0.035
            ax_bar.text(val + offset, bar.get_y() + bar.get_height()/2,
                        f'{val:+.3f}', va='center',
                        ha='left' if val >= 0 else 'right',
                        fontsize=12, fontweight='bold',
                        color=P['positive'] if val >= 0 else P['negative'])
        ax_bar.set_yticks(y_pos)
        ax_bar.set_yticklabels(cats, fontsize=13, color=P['dark'])
        ax_bar.set_xlabel('Composite Score  (S = 0.4·T + 0.3·D + 0.3·V)',
                          fontsize=11, color=P['mid'], labelpad=12)
        ax_bar.set_title('COMPOSITE C-QPAM SCORE BY CATEGORY',
                         fontsize=15, fontweight='bold', color=P['dark'], pad=18, loc='left')
        ax_bar.spines[['top','right','left']].set_visible(False)
        ax_bar.spines['bottom'].set_color(P['border'])
        ax_bar.grid(axis='x', color=P['grid'], linewidth=1, zorder=0)
        ax_bar.tick_params(axis='y', length=0, pad=10)
        ax_bar.tick_params(axis='x', colors=P['muted'])
        ax_bar.set_facecolor(P['card'])
        pos_p = mpatches.Patch(color=P['positive'], label='Prioritise — grow floor space & budget')
        neg_p = mpatches.Patch(color=P['negative'], label='Review — consider markdown or clearance')
        ax_bar.legend(handles=[pos_p, neg_p], fontsize=10, loc='lower right',
                      framealpha=0.95, edgecolor=P['border'])

        # ── Pie ───────────────────────────────────────────────────────
        ax_pie = fig.add_axes([0.05, 0.055, 0.38, 0.39])
        ax_pie.set_facecolor(P['card'])
        pos_df = df[df['floor_allocation_pct'] > 0]
        wedge_cols = [CAT_COLOURS[i % len(CAT_COLOURS)] for i in range(len(pos_df))]
        wedges, texts, ats = ax_pie.pie(
            pos_df['floor_allocation_pct'],
            labels=pos_df['category'],
            autopct='%1.1f%%',
            startangle=120,
            colors=wedge_cols,
            pctdistance=0.72,
            wedgeprops=dict(linewidth=2.5, edgecolor='white'),
            textprops=dict(fontsize=11),
        )
        for at in ats:
            at.set_fontsize(10); at.set_fontweight('bold'); at.set_color('white')
        ax_pie.set_title('FLOOR SPACE\nALLOCATION', fontsize=13,
                         fontweight='bold', color=P['dark'], pad=18)

        # ── Horizontal sqft bars ──────────────────────────────────────
        ax_fl = fig.add_axes([0.53, 0.055, 0.43, 0.39])
        ax_fl.set_facecolor(P['card'])
        sdf = df.sort_values('floor_sqft', ascending=True)
        bc  = [CAT_COLOURS[list(df['category']).index(c) % len(CAT_COLOURS)]
               for c in sdf['category']]
        fb  = ax_fl.barh(sdf['category'], sdf['floor_sqft'],
                         color=bc, height=0.55, edgecolor='white', linewidth=1.0)
        for bar, val in zip(fb, sdf['floor_sqft']):
            if val > 0:
                ax_fl.text(val + 6, bar.get_y() + bar.get_height()/2,
                           f'{val:.0f} sqft', va='center', fontsize=10.5, color=P['dark'])
        ax_fl.set_title('FLOOR SPACE (sq ft)', fontsize=13,
                        fontweight='bold', color=P['dark'], pad=18)
        ax_fl.spines[['top','right','left']].set_visible(False)
        ax_fl.spines['bottom'].set_color(P['border'])
        ax_fl.grid(axis='x', color=P['grid'], linewidth=1)
        ax_fl.tick_params(axis='y', labelsize=11, length=0, pad=8)
        ax_fl.tick_params(axis='x', colors=P['muted'])
        ax_fl.set_xlabel('Square Feet', fontsize=10, color=P['mid'])
        ax_fl.set_facecolor(P['card'])

        fig.savefig(f'{prefix}_page1.png', dpi=150, bbox_inches='tight', facecolor=P['bg'])
        plt.show()

    # ── PAGE 2: Operations Detail ──────────────────────────────────

    def _page2(self, df, shop_name, prefix):
        fig = plt.figure(figsize=(16, 20), facecolor=P['bg'])
        self._draw_header(
            fig, shop_name,
            'OPERATIONS DETAIL  ·  Weekly Budget  ·  Volunteer Hours  ·  Pricing Signals',
            'PAGE 2 OF 3', P['dark'], '#94A3B8'
        )

        # ── Budget bars ───────────────────────────────────────────────
        ax_bud = fig.add_axes([0.08, 0.665, 0.86, 0.25])
        ax_bud.set_facecolor(P['card'])
        bdf = df[df['budget_allocation'] > 0].sort_values('budget_allocation', ascending=False)
        bc  = [CAT_COLOURS[list(df['category']).index(c) % len(CAT_COLOURS)] for c in bdf['category']]
        bbs = ax_bud.bar(range(len(bdf)), bdf['budget_allocation'],
                         color=bc, width=0.52, edgecolor='white', linewidth=1.2)
        for bar, val in zip(bbs, bdf['budget_allocation']):
            ax_bud.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 4,
                        f'£{val:.0f}', ha='center', va='bottom',
                        fontsize=13, fontweight='bold', color=P['dark'])
        ax_bud.set_xticks(range(len(bdf)))
        ax_bud.set_xticklabels(bdf['category'], fontsize=13, color=P['dark'])
        ax_bud.set_ylabel('Weekly Budget (£)', fontsize=11, color=P['mid'], labelpad=10)
        ax_bud.set_title(f'WEEKLY BUDGET ALLOCATION  —  Total: £{self.weekly_budget:,.0f}',
                         fontsize=15, fontweight='bold', color=P['dark'], pad=18, loc='left')
        ax_bud.spines[['top','right','left']].set_visible(False)
        ax_bud.spines['bottom'].set_color(P['border'])
        ax_bud.grid(axis='y', color=P['grid'], linewidth=1)
        ax_bud.tick_params(axis='x', length=0, pad=10)
        ax_bud.tick_params(axis='y', colors=P['muted'])
        ax_bud.set_facecolor(P['card'])
        equal = self.weekly_budget / len(bdf)
        ax_bud.axhline(equal, color=P['muted'], linewidth=1.2, linestyle='--', alpha=0.7)
        ax_bud.text(len(bdf)-0.5, equal + 3, 'Equal-split baseline',
                    fontsize=8.5, color=P['muted'], ha='right')

        # ── Volunteer bars ────────────────────────────────────────────
        ax_vol = fig.add_axes([0.08, 0.380, 0.86, 0.25])
        ax_vol.set_facecolor(P['card'])
        vdf = df.sort_values('volunteer_hours', ascending=False)
        vc  = [CAT_COLOURS[list(df['category']).index(c) % len(CAT_COLOURS)] for c in vdf['category']]
        vbs = ax_vol.bar(range(len(vdf)), vdf['volunteer_hours'],
                         color=vc, width=0.52, edgecolor='white', linewidth=1.2)
        for bar, val in zip(vbs, vdf['volunteer_hours']):
            ax_vol.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                        f'{val:.1f} hrs', ha='center', va='bottom',
                        fontsize=12, fontweight='bold', color=P['dark'])
        ax_vol.axhline(self.min_hours_per_cat, color=P['negative'],
                       linewidth=1.8, linestyle='--', alpha=0.8)
        ax_vol.text(len(vdf)-0.5, self.min_hours_per_cat + 0.25,
                    f'Guaranteed minimum ({self.min_hours_per_cat} hrs/cat)',
                    fontsize=9, color=P['negative'], ha='right')
        ax_vol.set_xticks(range(len(vdf)))
        ax_vol.set_xticklabels(vdf['category'], fontsize=13, color=P['dark'])
        ax_vol.set_ylabel('Hours per Week', fontsize=11, color=P['mid'], labelpad=10)
        ax_vol.set_title(
            f'VOLUNTEER HOURS  —  Total: {self.weekly_volunteer_hours} hrs  ·  '
            f'Min {self.min_hours_per_cat} hrs guaranteed per category',
            fontsize=15, fontweight='bold', color=P['dark'], pad=18, loc='left')
        ax_vol.spines[['top','right','left']].set_visible(False)
        ax_vol.spines['bottom'].set_color(P['border'])
        ax_vol.grid(axis='y', color=P['grid'], linewidth=1)
        ax_vol.tick_params(axis='x', length=0, pad=10)
        ax_vol.tick_params(axis='y', colors=P['muted'])
        ax_vol.set_facecolor(P['card'])

        # ── Pricing signals table ────────────────────────────────────
        ax_pr = fig.add_axes([0.05, 0.055, 0.90, 0.295])
        ax_pr.set_facecolor(P['card'])
        ax_pr.axis('off')
        ax_pr.set_title('PRICING SIGNALS & SELL-THROUGH ANALYSIS',
                        fontsize=15, fontweight='bold', color=P['dark'], pad=18, loc='left', x=0)

        signal_meta = {
            '▲ PREMIUM':  (P['positive'],  P['pos_lt'],   'Do not discount — sell-through is high, demand exceeds supply'),
            '= HOLD':     (P['dark'],       '#F7FAFC',     'Maintain current pricing — performance is on target'),
            '▼ DISCOUNT': (P['amber'],      P['amber_lt'], 'Apply 20–30% reduction to accelerate clearance'),
            '▼ MARKDOWN': (P['negative'],   P['neg_lt'],   'Urgent clearance needed — 50%+ off, bag-sale, or donate-on'),
        }

        col_headers = ['CATEGORY', 'C-QPAM SCORE', 'SELL-THROUGH', 'TOTAL REVENUE', 'SIGNAL', 'RECOMMENDED ACTION']
        col_x       = [0.01, 0.19, 0.34, 0.49, 0.64, 0.79]
        col_align   = ['left','center','center','center','center','left']

        # Header background
        ax_pr.add_patch(FancyBboxPatch((0, 0.875), 1, 0.10,
                                       boxstyle='square,pad=0',
                                       facecolor=P['dark'], edgecolor='none',
                                       transform=ax_pr.transAxes))
        for hdr, x, al in zip(col_headers, col_x, col_align):
            ax_pr.text(x, 0.928, hdr, transform=ax_pr.transAxes,
                       fontsize=10, fontweight='bold', color='white',
                       ha=al, va='center', zorder=5)

        row_h   = 0.118
        start_y = 0.855
        for i, (_, row) in enumerate(df.sort_values('score', ascending=False).iterrows()):
            y   = start_y - i * row_h
            sig = row['pricing_signal']
            sc, bg, action = signal_meta.get(sig, (P['dark'], '#FFFFFF', ''))
            bg_col = bg if i % 2 == 0 else P['card']
            ax_pr.add_patch(FancyBboxPatch((0, y - row_h*0.83), 1, row_h*0.88,
                                           boxstyle='square,pad=0',
                                           facecolor=bg_col, edgecolor=P['border'],
                                           linewidth=0.5, transform=ax_pr.transAxes))
            vals = [
                row['category'],
                f"{row['score']:+.3f}",
                f"{row['sellthrough']:.1%}",
                f"£{row['total_revenue']:,.0f}",
                sig,
                action,
            ]
            row_y = y - row_h*0.33
            for val, x, al in zip(vals, col_x, col_align):
                clr = sc if (val == sig) else P['dark']
                wt  = 'bold' if (val == sig or val == row['category']) else 'normal'
                ax_pr.text(x, row_y, val, transform=ax_pr.transAxes,
                           fontsize=10.5, color=clr, ha=al, va='center', fontweight=wt)

        fig.savefig(f'{prefix}_page2.png', dpi=150, bbox_inches='tight', facecolor=P['bg'])
        plt.show()

    # ── PAGE 3: Factor Deep-Dive + Full Table ──────────────────────

    def _page3(self, df, shop_name, prefix):
        fig = plt.figure(figsize=(16, 20), facecolor=P['bg'])
        self._draw_header(
            fig, shop_name,
            'FACTOR DEEP-DIVE  ·  T / D / V Breakdown  ·  Full Allocation Summary Table',
            'PAGE 3 OF 3', '#1B6B3A', '#A7F3D0'
        )

        # ── Factor legend strip ───────────────────────────────────────
        ax_leg = fig.add_axes([0.05, 0.870, 0.90, 0.055])
        ax_leg.set_facecolor('#EFF6FF'); ax_leg.axis('off')
        ax_leg.add_patch(FancyBboxPatch((0,0), 1, 1, boxstyle='round,pad=0.02',
                                        linewidth=1.2, edgecolor='#BFDBFE',
                                        facecolor='#EFF6FF', transform=ax_leg.transAxes))
        entries = [
            ('T — Turnover Momentum',      f"Weight {self.weights['T']:.0%}",
             'Sell-through rate normalised vs category mean. Higher = stock moving faster.'),
            ('D — Donation Mean Reversion', f"Weight {self.weights['D']:.0%}",
             'Donation surplus today → negative signal (expect glut). Shortage → positive.'),
            ('V — Volatility Reliability',  f"Weight {self.weights['V']:.0%}",
             'Predictable donation flow earns a reliability premium in the composite score.'),
        ]
        for i, (name, wt, desc) in enumerate(entries):
            x = 0.02 + i*0.335
            ax_leg.text(x, 0.80, name, transform=ax_leg.transAxes,
                        fontsize=10.5, fontweight='bold', color=P['dark'])
            ax_leg.text(x + 0.165, 0.80, wt, transform=ax_leg.transAxes,
                        fontsize=9.5, color=P['primary'], fontweight='bold')
            ax_leg.text(x, 0.24, desc, transform=ax_leg.transAxes,
                        fontsize=8.5, color=P['mid'])

        # ── Heatmap ───────────────────────────────────────────────────
        ax_ht = fig.add_axes([0.06, 0.585, 0.86, 0.265])
        ax_ht.set_facecolor(P['card'])
        cats_s     = df['category'].tolist()
        heat_data  = df[['T','D','V']].values.T
        factor_lab = ['Turnover\nMomentum (T)', 'Donation\nMean Rev. (D)', 'Vol. Reliability (V)']
        cmap       = plt.cm.RdYlGn
        im = ax_ht.imshow(heat_data, aspect='auto', cmap=cmap,
                          vmin=-2.2, vmax=2.2, interpolation='nearest')
        ax_ht.set_xticks(range(len(cats_s)))
        ax_ht.set_xticklabels(cats_s, fontsize=12, color=P['dark'])
        ax_ht.set_yticks(range(3))
        ax_ht.set_yticklabels(factor_lab, fontsize=12, color=P['dark'])
        ax_ht.tick_params(axis='both', length=0, pad=10)
        for row in range(3):
            for col in range(len(cats_s)):
                val  = heat_data[row, col]
                tc   = 'white' if abs(val) > 1.2 else P['dark']
                ax_ht.text(col, row, f'{val:.2f}', ha='center', va='center',
                           fontsize=14, fontweight='bold', color=tc)
        cb = plt.colorbar(im, ax=ax_ht, shrink=0.72, pad=0.015)
        cb.set_label('Z-Score  (−2 = weak  →  +2 = strong)', fontsize=10, color=P['mid'])
        ax_ht.set_title('FACTOR SCORES HEATMAP  (Z-Score Normalised)',
                        fontsize=15, fontweight='bold', color=P['dark'], pad=18, loc='left')

        # ── Full Summary Table ────────────────────────────────────────
        ax_tb = fig.add_axes([0.03, 0.055, 0.94, 0.500])
        ax_tb.set_facecolor(P['card']); ax_tb.axis('off')
        ax_tb.set_title('FULL ALLOCATION SUMMARY TABLE',
                        fontsize=15, fontweight='bold', color=P['dark'],
                        pad=18, loc='left', x=0)

        cols      = ['Category','Score','T','D','V','Floor %','sqft','Budget £',
                     'Vol. Hrs','Sell-Through','Rev/sqft','Signal']
        col_x     = [0.01, 0.11, 0.20, 0.27, 0.34, 0.42, 0.51, 0.60,
                     0.69, 0.78, 0.88, 0.945]
        col_align = ['left','center','center','center','center','center','center',
                     'center','center','center','center','center']

        # Table header
        ax_tb.add_patch(FancyBboxPatch((0, 0.900), 1, 0.075,
                                       boxstyle='square,pad=0',
                                       facecolor=P['dark'], edgecolor='none',
                                       transform=ax_tb.transAxes))
        for hdr, x, al in zip(cols, col_x, col_align):
            ax_tb.text(x, 0.939, hdr, transform=ax_tb.transAxes,
                       fontsize=9.5, fontweight='bold', color='white',
                       ha=al, va='center', zorder=5)

        row_h   = 0.108
        start_y = 0.885
        for i, (_, row) in enumerate(df.sort_values('score', ascending=False).iterrows()):
            y  = start_y - i * row_h
            sc = row['score']
            bg = (P['pos_lt'] if sc >= 0.5
                  else P['neg_lt'] if sc < 0
                  else '#F7FAFC')
            ax_tb.add_patch(FancyBboxPatch((0, y - row_h*0.80), 1, row_h*0.86,
                                           boxstyle='square,pad=0',
                                           facecolor=bg, edgecolor=P['border'],
                                           linewidth=0.5, transform=ax_tb.transAxes))
            rsq  = row['rev_per_sqft']
            vals = [
                row['category'],
                f"{sc:+.3f}",
                f"{row['T']:+.2f}", f"{row['D']:+.2f}", f"{row['V']:+.2f}",
                f"{row['floor_allocation_pct']:.1%}",
                f"{row['floor_sqft']:.0f}",
                f"£{row['budget_allocation']:.0f}",
                f"{row['volunteer_hours']:.1f}",
                f"{row['sellthrough']:.1%}",
                f"£{rsq:.2f}" if not np.isnan(rsq) else 'N/A',
                row['pricing_signal'],
            ]
            row_y = y - row_h*0.28
            for val, x, al in zip(vals, col_x, col_align):
                is_score  = (val == f"{sc:+.3f}")
                is_signal = (val == row['pricing_signal'])
                clr = (P['positive'] if (is_score or is_signal) and sc >= 0.5
                       else P['negative'] if (is_score or is_signal) and sc < 0
                       else P['amber']   if (is_score or is_signal)
                       else P['dark'])
                wt  = 'bold' if (is_score or is_signal or val == row['category']) else 'normal'
                ax_tb.text(x, row_y, val, transform=ax_tb.transAxes,
                           fontsize=10.5, color=clr, ha=al, va='center', fontweight=wt)

        fig.savefig(f'{prefix}_page3.png', dpi=150, bbox_inches='tight', facecolor=P['bg'])
        plt.show()


# ─────────────────────────────────────────────────────────────────
#   DUMMY DATA GENERATOR
# ─────────────────────────────────────────────────────────────────

def generate_dummy_data(n_weeks=12, seed=42):
    rng = np.random.default_rng(seed)
    profiles = {
        'Clothing':        (45, 12, 0.85, 4.50),
        'Books':           (60, 8,  0.75, 1.20),
        'Homeware':        (30, 15, 0.60, 3.80),
        'Electronics':     (10, 6,  0.90, 12.00),
        'Toys':            (25, 10, 0.65, 2.50),
        'Bric-a-Brac':     (50, 20, 0.35, 1.50),
        'Furniture':       (8,  5,  0.70, 35.00),
        'Media (DVD/CD)':  (35, 7,  0.40, 0.80),
    }
    sales_rows, donation_rows = [], []
    for week in range(1, n_weeks + 1):
        for cat, (mu_d, sig_d, sell_rate, price) in profiles.items():
            donated = max(1, int(rng.normal(mu_d, sig_d)))
            if week >= n_weeks - 1 and cat in ['Clothing', 'Bric-a-Brac']:
                donated = int(donated * 1.8)
            sold    = min(max(0, int(donated * rng.normal(sell_rate, 0.08))), donated)
            revenue = round(sold * price * rng.uniform(0.9, 1.1), 2)
            donation_rows.append({'week': week, 'category': cat, 'units_donated': donated})
            sales_rows.append({'week': week, 'category': cat,
                               'units_sold': sold, 'revenue': revenue})
    expense_rows = [
        {'category': 'SHOP',        'expense_type': 'Rent',         'amount': 1800.00},
        {'category': 'SHOP',        'expense_type': 'Utilities',     'amount': 240.00},
        {'category': 'SHOP',        'expense_type': 'Insurance',     'amount': 95.00},
        {'category': 'Clothing',    'expense_type': 'Steamer/Rail',  'amount': 25.00},
        {'category': 'Electronics', 'expense_type': 'PAT Testing',   'amount': 40.00},
        {'category': 'Furniture',   'expense_type': 'Delivery Fuel', 'amount': 60.00},
        {'category': 'SHOP',        'expense_type': 'Supplies/Bags', 'amount': 35.00},
    ]
    return pd.DataFrame(sales_rows), pd.DataFrame(donation_rows), pd.DataFrame(expense_rows)


# ─────────────────────────────────────────────────────────────────
#   TEXT REPORT
# ─────────────────────────────────────────────────────────────────

def print_text_report(model: CharityQPAM):
    df = model.factor_df_.reset_index()
    div = "─" * 72
    print(f"\n{'═'*72}")
    print(f"  C-QPAM  ·  Axiom Capital Research  ·  Charity Allocation Report")
    print(f"{'═'*72}")

    print(f"\nFLOOR SPACE RECOMMENDATIONS")
    print(div)
    for _, r in df.sort_values('floor_allocation_pct', ascending=False).iterrows():
        bar = '█' * int(r['floor_allocation_pct'] * 30)
        print(f"  {r['category']:<18} {bar:<30} {r['floor_allocation_pct']:>5.1%}  ({r['floor_sqft']:.0f} sqft)")

    print(f"\nPRICING SIGNALS")
    print(div)
    for _, r in df.sort_values('score').iterrows():
        print(f"  {r['category']:<18} {r['pricing_signal']:<16}"
              f"  Sell-through: {r['sellthrough']:.1%}   Score: {r['score']:+.3f}")

    print(f"\nBUDGET ALLOCATION  (£{model.weekly_budget:,.0f}/week)")
    print(div)
    for _, r in df[df['budget_allocation']>0].sort_values('budget_allocation', ascending=False).iterrows():
        print(f"  {r['category']:<18} £{r['budget_allocation']:>7.2f}")

    print(f"\nVOLUNTEER HOURS  ({model.weekly_volunteer_hours} hrs/week"
          f"  ·  min {model.min_hours_per_cat} hrs/cat guaranteed)")
    print(div)
    for _, r in df.sort_values('volunteer_hours', ascending=False).iterrows():
        print(f"  {r['category']:<18} {r['volunteer_hours']:>5.1f} hrs")

    print(f"\nSUMMARY TABLE")
    print(div)
    s = df[['category','score','floor_allocation_pct','floor_sqft',
            'budget_allocation','volunteer_hours','pricing_signal']].copy()
    s.columns = ['Category','Score','Floor%','sqft','Budget£','Vol.Hrs','Signal']
    s['Score']  = s['Score'].map('{:+.3f}'.format)
    s['Floor%'] = s['Floor%'].map('{:.1%}'.format)
    print(s.to_string(index=False))
    print(f"\n{'═'*72}\n")


# ─────────────────────────────────────────────────────────────────
#   MAIN
# ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    sales_df, donations_df, expenses_df = generate_dummy_data(n_weeks=12)

    model = CharityQPAM(
        weights={'T': 0.4, 'D': 0.3, 'V': 0.3},
        total_floor_sqft=1200,
        weekly_budget=800,
        weekly_volunteer_hours=120,
        min_hours_per_cat=2.0,
    )
    model.fit(sales_df, donations_df, expenses_df)
    print_text_report(model)
    model.report(shop_name="British Heart Foundation – Chiswick Branch", save_prefix="cqpam")
