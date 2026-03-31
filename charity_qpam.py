"""
╔══════════════════════════════════════════════════════════════════╗
║          C-QPAM: Charity Quantitative Portfolio Allocation       ║
║          Adapted from QPAM framework by Axiom Capital Research   ║
╚══════════════════════════════════════════════════════════════════╝

Run in Jupyter Notebook for full visual output.
Install dependencies: pip install pandas numpy matplotlib seaborn
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch
import matplotlib.patches as mpatches
import warnings
warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────
#  COLOUR PALETTE  (charity-sector warm tones)
# ─────────────────────────────────────────────
PALETTE = {
    'bg':        '#FAF7F2',
    'card':      '#FFFFFF',
    'primary':   '#C0392B',   # BHF/Oxfam charity red
    'secondary': '#2C3E50',
    'accent':    '#E67E22',
    'positive':  '#27AE60',
    'negative':  '#E74C3C',
    'neutral':   '#95A5A6',
    'text':      '#2C3E50',
    'subtext':   '#7F8C8D',
    'grid':      '#ECF0F1',
}

# ─────────────────────────────────────────────────────
#   CharityQPAM  CLASS
# ─────────────────────────────────────────────────────

class CharityQPAM:
    """
    Charity Quantitative Portfolio Allocation Model.

    Adapts quantitative finance factor logic to charity retail operations:

      Factor 1 – Turnover Momentum (T):   sell-through velocity vs donations
      Factor 2 – Donation Mean Reversion (D): surplus/shortage signal
      Factor 3 – Volatility Reliability (V): predictability multiplier

      Score S_i = 0.4·T_i + 0.3·D_i + 0.3·V_i
      Allocation w_i = max(S_i,0) / Σ max(S_j,0)

    Parameters
    ----------
    weights : dict, optional
        Factor weights, default {'T': 0.4, 'D': 0.3, 'V': 0.3}.
    total_floor_sqft : float
        Total sellable floor space in square feet.
    weekly_budget : float
        Weekly discretionary operating budget (£).
    weekly_volunteer_hours : float
        Total volunteer hours available per week.
    """

    def __init__(
        self,
        weights=None,
        total_floor_sqft: float = 1200,
        weekly_budget: float = 800,
        weekly_volunteer_hours: float = 120,
    ):
        self.weights = weights or {'T': 0.4, 'D': 0.3, 'V': 0.3}
        assert abs(sum(self.weights.values()) - 1.0) < 1e-6, "Weights must sum to 1."
        self.total_floor_sqft = total_floor_sqft
        self.weekly_budget = weekly_budget
        self.weekly_volunteer_hours = weekly_volunteer_hours

        # Populated after fit()
        self.categories_ = None
        self.scores_ = None
        self.allocations_ = None
        self.factor_df_ = None
        self.raw_data_ = None

    # ──────────────────────────────────────────
    #   FIT
    # ──────────────────────────────────────────

    def fit(
        self,
        sales_df: pd.DataFrame,
        donations_df: pd.DataFrame,
        expenses_df: pd.DataFrame,
    ):
        """
        Fit the model on weekly data.

        Parameters
        ----------
        sales_df : pd.DataFrame
            Columns: ['week', 'category', 'units_sold', 'revenue']
        donations_df : pd.DataFrame
            Columns: ['week', 'category', 'units_donated']
        expenses_df : pd.DataFrame
            Columns: ['category', 'expense_type', 'amount']
            (category='SHOP' for shop-wide expenses)
        """
        self.raw_data_ = {
            'sales': sales_df.copy(),
            'donations': donations_df.copy(),
            'expenses': expenses_df.copy(),
        }

        cats = sorted(sales_df['category'].unique())
        self.categories_ = cats

        # ── Aggregate per category ──────────────────────────────────────
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

        # ── Latest week donation vs mean (for mean-reversion) ──────────
        latest_week = donations_df['week'].max()
        latest_don = (
            donations_df[donations_df['week'] == latest_week]
            .set_index('category')['units_donated']
        )
        df['latest_donated'] = df['category'].map(latest_don).fillna(0)

        # ── Factor 1: Turnover Momentum ─────────────────────────────────
        # T_raw = sold / donated  (sell-through ratio)
        df['sellthrough'] = df['total_units_sold'] / df['total_donated'].replace(0, np.nan)
        df['sellthrough'] = df['sellthrough'].fillna(0)
        mean_st = df['sellthrough'].mean()
        df['T_raw'] = df['sellthrough'] / (mean_st if mean_st > 0 else 1)

        # Z-score normalise
        df['T'] = self._zscore(df['T_raw'])

        # ── Factor 2: Donation Mean Reversion ───────────────────────────
        # D_raw = -(latest - mean) / std  → surplus = negative signal
        df['D_raw'] = -(df['latest_donated'] - df['avg_donated']) / (df['std_donated'].replace(0, 1))
        df['D'] = self._zscore(df['D_raw'])

        # ── Factor 3: Volatility Reliability ────────────────────────────
        # V = 1 - normalised_std  (lower vol = more reliable = higher score)
        max_std = df['std_donated'].max()
        if max_std > 0:
            df['V_raw'] = 1 - (df['std_donated'] / max_std)
        else:
            df['V_raw'] = 1.0
        df['V'] = self._zscore(df['V_raw'])

        # ── Composite Score ──────────────────────────────────────────────
        w = self.weights
        df['score'] = (
            w['T'] * df['T'] +
            w['D'] * df['D'] +
            w['V'] * df['V']
        )

        # ── Floor Space Allocation (positive-score categories only) ──────
        df['score_clipped'] = df['score'].clip(lower=0)
        total_pos = df['score_clipped'].sum()
        df['floor_allocation_pct'] = (
            df['score_clipped'] / total_pos if total_pos > 0 else 1 / len(df)
        )
        df['floor_sqft'] = (df['floor_allocation_pct'] * self.total_floor_sqft).round(0)

        # ── Budget Allocation (same weights as floor) ────────────────────
        df['budget_allocation'] = (df['floor_allocation_pct'] * self.weekly_budget).round(2)

        # ── Volunteer Hours (weighted by turnover momentum) ──────────────
        t_pos = df['T'].clip(lower=0)
        df['volunteer_hours'] = (
            (t_pos / t_pos.sum() * self.weekly_volunteer_hours)
            .round(1)
            if t_pos.sum() > 0
            else self.weekly_volunteer_hours / len(df)
        )

        # ── Pricing Signal ───────────────────────────────────────────────
        df['pricing_signal'] = df.apply(self._pricing_signal, axis=1)

        # ── Revenue per sq ft (efficiency metric) ────────────────────────
        df['rev_per_sqft'] = (df['total_revenue'] / df['floor_sqft'].replace(0, np.nan)).round(2)

        self.factor_df_ = df.set_index('category')
        self.scores_ = df.set_index('category')['score']
        self.allocations_ = df.set_index('category')['floor_allocation_pct']

        return self

    # ──────────────────────────────────────────
    #   HELPERS
    # ──────────────────────────────────────────

    @staticmethod
    def _zscore(series: pd.Series) -> pd.Series:
        std = series.std()
        if std == 0:
            return pd.Series(0.0, index=series.index)
        return (series - series.mean()) / std

    @staticmethod
    def _pricing_signal(row) -> str:
        score = row['score']
        st    = row['sellthrough']
        if score > 0.5 and st > 0.8:
            return '▲ PREMIUM'
        elif score > 0 and st > 0.5:
            return '= HOLD'
        elif score < 0 and st < 0.4:
            return '▼ MARKDOWN'
        else:
            return '▼ DISCOUNT'

    # ──────────────────────────────────────────
    #   REPORT
    # ──────────────────────────────────────────

    def report(self, shop_name: str = "C-QPAM Charity Shop Report"):
        """Generate the full visual report (call inside Jupyter)."""
        df = self.factor_df_.copy().reset_index()

        fig = plt.figure(figsize=(20, 26), facecolor=PALETTE['bg'])
        fig.suptitle('')

        gs = gridspec.GridSpec(
            5, 3,
            figure=fig,
            hspace=0.55,
            wspace=0.35,
            top=0.93,
            bottom=0.04,
            left=0.05,
            right=0.97,
        )

        # ── HEADER ────────────────────────────────────────────────────
        ax_header = fig.add_subplot(gs[0, :])
        ax_header.set_facecolor(PALETTE['secondary'])
        ax_header.axis('off')
        ax_header.text(
            0.5, 0.72, shop_name,
            transform=ax_header.transAxes,
            fontsize=22, fontweight='bold',
            color='white', ha='center', va='center',
            fontfamily='DejaVu Sans',
        )
        ax_header.text(
            0.5, 0.25,
            f"Axiom Capital Research · C-QPAM v1.0  ·  "
            f"Weights: T={self.weights['T']}  D={self.weights['D']}  V={self.weights['V']}  ·  "
            f"Floor: {self.total_floor_sqft:,.0f} sq ft  ·  "
            f"Budget: £{self.weekly_budget:,.0f}/wk  ·  "
            f"Volunteer hrs: {self.weekly_volunteer_hours}",
            transform=ax_header.transAxes,
            fontsize=9.5, color='#BDC3C7', ha='center', va='center',
        )

        # ── ROW 1: Composite Score Bar + Floor Allocation Pie ─────────
        ax_score = fig.add_subplot(gs[1, :2])
        self._plot_score_bar(ax_score, df)

        ax_pie = fig.add_subplot(gs[1, 2])
        self._plot_pie(ax_pie, df)

        # ── ROW 2: Factor Heatmap + Pricing Table ─────────────────────
        ax_heat = fig.add_subplot(gs[2, :2])
        self._plot_factor_heatmap(ax_heat, df)

        ax_price = fig.add_subplot(gs[2, 2])
        self._plot_pricing_table(ax_price, df)

        # ── ROW 3: Budget bar + Volunteer Hours ───────────────────────
        ax_budget = fig.add_subplot(gs[3, :2])
        self._plot_budget(ax_budget, df)

        ax_vol = fig.add_subplot(gs[3, 2])
        self._plot_volunteer(ax_vol, df)

        # ── ROW 4: Allocation Summary Table ───────────────────────────
        ax_table = fig.add_subplot(gs[4, :])
        self._plot_summary_table(ax_table, df)

        plt.savefig('cqpam_report.png', dpi=150, bbox_inches='tight',
                    facecolor=PALETTE['bg'])
        plt.show()
        print("\n✓ Report saved to cqpam_report.png")

    # ──────────────────────────────────────────
    #   PLOT HELPERS
    # ──────────────────────────────────────────

    def _plot_score_bar(self, ax, df):
        ax.set_facecolor(PALETTE['card'])
        cats = df['category']
        scores = df['score']
        colours = [PALETTE['positive'] if s >= 0 else PALETTE['negative'] for s in scores]

        bars = ax.barh(cats, scores, color=colours, edgecolor='white',
                       linewidth=0.6, height=0.6)
        ax.axvline(0, color=PALETTE['secondary'], linewidth=1.2, linestyle='--', alpha=0.6)

        for bar, val in zip(bars, scores):
            ax.text(
                val + (0.03 if val >= 0 else -0.03),
                bar.get_y() + bar.get_height() / 2,
                f'{val:+.3f}',
                va='center', ha='left' if val >= 0 else 'right',
                fontsize=8.5, color=PALETTE['text'], fontweight='bold',
            )

        ax.set_title('Composite C-QPAM Score by Category',
                     fontsize=12, fontweight='bold', color=PALETTE['text'], pad=8)
        ax.set_xlabel('Score  (S = 0.4·T + 0.3·D + 0.3·V)', fontsize=9, color=PALETTE['subtext'])
        ax.tick_params(axis='y', labelsize=9.5)
        ax.spines[['top', 'right', 'left']].set_visible(False)
        ax.grid(axis='x', color=PALETTE['grid'], linewidth=0.8)

        pos_patch = mpatches.Patch(color=PALETTE['positive'], label='Prioritise ↑')
        neg_patch = mpatches.Patch(color=PALETTE['negative'], label='Review / Markdown ↓')
        ax.legend(handles=[pos_patch, neg_patch], fontsize=8, loc='lower right')

    def _plot_pie(self, ax, df):
        pos = df[df['floor_allocation_pct'] > 0]
        ax.pie(
            pos['floor_allocation_pct'],
            labels=pos['category'],
            autopct='%1.1f%%',
            startangle=140,
            colors=plt.cm.Set2.colors[:len(pos)],
            pctdistance=0.78,
            textprops={'fontsize': 8},
        )
        ax.set_title('Floor Space Allocation', fontsize=11,
                     fontweight='bold', color=PALETTE['text'])

    def _plot_factor_heatmap(self, ax, df):
        import matplotlib.colors as mcolors

        heat_data = df[['category', 'T', 'D', 'V']].set_index('category')
        factor_labels = {
            'T': 'Turnover\nMomentum',
            'D': 'Donation\nMean Rev.',
            'V': 'Volatility\nReliability',
        }
        heat_data.columns = [factor_labels[c] for c in heat_data.columns]

        cmap = plt.cm.RdYlGn
        im = ax.imshow(heat_data.values.T, aspect='auto', cmap=cmap, vmin=-2, vmax=2)

        ax.set_xticks(range(len(heat_data.index)))
        ax.set_xticklabels(heat_data.index, fontsize=9)
        ax.set_yticks(range(len(heat_data.columns)))
        ax.set_yticklabels(heat_data.columns, fontsize=9)

        for i in range(len(heat_data.columns)):
            for j in range(len(heat_data.index)):
                val = heat_data.values[j, i]
                ax.text(j, i, f'{val:.2f}', ha='center', va='center',
                        fontsize=8.5, fontweight='bold',
                        color='white' if abs(val) > 1 else PALETTE['text'])

        plt.colorbar(im, ax=ax, shrink=0.8, label='Z-Score')
        ax.set_title('Factor Scores Heatmap (Z-Scores)',
                     fontsize=11, fontweight='bold', color=PALETTE['text'])

    def _plot_pricing_table(self, ax, df):
        ax.set_facecolor(PALETTE['card'])
        ax.axis('off')
        ax.set_title('Pricing Signals', fontsize=11,
                     fontweight='bold', color=PALETTE['text'], pad=8)

        rows = df[['category', 'sellthrough', 'pricing_signal']].values
        col_labels = ['Category', 'Sell-Through', 'Signal']

        row_colours = []
        for row in rows:
            sig = row[2]
            if 'PREMIUM' in sig:
                row_colours.append([PALETTE['positive'] + '33'] * 3)
            elif 'MARKDOWN' in sig or 'DISCOUNT' in sig:
                row_colours.append([PALETTE['negative'] + '33'] * 3)
            else:
                row_colours.append(['#FFFFFF'] * 3)

        table_data = [[r[0], f"{r[1]:.1%}", r[2]] for r in rows]

        tbl = ax.table(
            cellText=table_data,
            colLabels=col_labels,
            cellLoc='center',
            loc='center',
            cellColours=row_colours,
        )
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(8.5)
        tbl.scale(1, 1.6)

        for (row, col), cell in tbl.get_celld().items():
            if row == 0:
                cell.set_facecolor(PALETTE['secondary'])
                cell.set_text_props(color='white', fontweight='bold')
            cell.set_edgecolor(PALETTE['grid'])

    def _plot_budget(self, ax, df):
        ax.set_facecolor(PALETTE['card'])
        pos = df[df['budget_allocation'] > 0]
        bars = ax.bar(pos['category'], pos['budget_allocation'],
                      color=PALETTE['accent'], edgecolor='white',
                      linewidth=0.6, width=0.5)
        for bar, val in zip(bars, pos['budget_allocation']):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 3,
                    f'£{val:.0f}', ha='center', va='bottom',
                    fontsize=8.5, fontweight='bold', color=PALETTE['text'])

        ax.set_title(f'Weekly Budget Allocation  (Total: £{self.weekly_budget:,.0f})',
                     fontsize=11, fontweight='bold', color=PALETTE['text'], pad=8)
        ax.set_ylabel('Budget (£)', fontsize=9, color=PALETTE['subtext'])
        ax.spines[['top', 'right']].set_visible(False)
        ax.grid(axis='y', color=PALETTE['grid'], linewidth=0.8)
        ax.tick_params(axis='x', labelsize=9)

    def _plot_volunteer(self, ax, df):
        ax.set_facecolor(PALETTE['card'])
        sorted_df = df.sort_values('volunteer_hours', ascending=True)
        bars = ax.barh(sorted_df['category'], sorted_df['volunteer_hours'],
                       color=PALETTE['primary'], edgecolor='white', height=0.5)
        for bar, val in zip(bars, sorted_df['volunteer_hours']):
            ax.text(val + 0.3, bar.get_y() + bar.get_height() / 2,
                    f'{val:.1f} hrs', va='center', fontsize=8.5,
                    color=PALETTE['text'])
        ax.set_title('Volunteer Hours\nAllocation', fontsize=11,
                     fontweight='bold', color=PALETTE['text'], pad=8)
        ax.spines[['top', 'right', 'left']].set_visible(False)
        ax.grid(axis='x', color=PALETTE['grid'], linewidth=0.8)
        ax.tick_params(labelsize=9)

    def _plot_summary_table(self, ax, df):
        ax.set_facecolor(PALETTE['card'])
        ax.axis('off')
        ax.set_title('C-QPAM Allocation Summary Table',
                     fontsize=12, fontweight='bold', color=PALETTE['text'],
                     pad=10, loc='left')

        cols = [
            'Category', 'Score', 'Floor %', 'Floor (sqft)',
            'Budget (£)', 'Vol. Hrs', 'Sell-Through', 'Rev/sqft (£)', 'Signal'
        ]
        rows_data = []
        for _, row in df.iterrows():
            rows_data.append([
                row['category'],
                f"{row['score']:+.3f}",
                f"{row['floor_allocation_pct']:.1%}",
                f"{row['floor_sqft']:.0f}",
                f"£{row['budget_allocation']:.0f}",
                f"{row['volunteer_hours']:.1f}",
                f"{row['sellthrough']:.1%}",
                f"£{row['rev_per_sqft']:.2f}" if not np.isnan(row['rev_per_sqft']) else 'N/A',
                row['pricing_signal'],
            ])

        row_colours = []
        for row in df.itertuples():
            if row.score >= 0.5:
                row_colours.append([PALETTE['positive'] + '22'] * len(cols))
            elif row.score < 0:
                row_colours.append([PALETTE['negative'] + '22'] * len(cols))
            else:
                row_colours.append(['#FFFFFF'] * len(cols))

        tbl = ax.table(
            cellText=rows_data,
            colLabels=cols,
            cellLoc='center',
            loc='center',
            cellColours=row_colours,
        )
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(9)
        tbl.scale(1, 1.8)

        for (row, col), cell in tbl.get_celld().items():
            if row == 0:
                cell.set_facecolor(PALETTE['secondary'])
                cell.set_text_props(color='white', fontweight='bold', fontsize=9)
                cell.set_height(0.12)
            cell.set_edgecolor(PALETTE['grid'])


# ─────────────────────────────────────────────────────────────────
#   DUMMY DATA GENERATOR
# ─────────────────────────────────────────────────────────────────

def generate_dummy_data(n_weeks: int = 12, seed: int = 42) -> tuple:
    """
    Generate realistic dummy data for a charity shop across 8 categories.

    Returns
    -------
    sales_df, donations_df, expenses_df
    """
    rng = np.random.default_rng(seed)

    categories = [
        'Clothing', 'Books', 'Homeware', 'Electronics',
        'Toys', 'Bric-a-Brac', 'Furniture', 'Media (DVD/CD)'
    ]

    # Category characteristics (mean_donated, std_donated, sell_rate, avg_price)
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
            # Simulate occasional donation surge in final 2 weeks for some cats
            if week >= n_weeks - 1 and cat in ['Clothing', 'Bric-a-Brac']:
                donated = int(donated * 1.8)

            sold = max(0, int(donated * rng.normal(sell_rate, 0.08)))
            sold = min(sold, donated)
            revenue = round(sold * price * rng.uniform(0.9, 1.1), 2)

            donation_rows.append({'week': week, 'category': cat, 'units_donated': donated})
            sales_rows.append({
                'week': week, 'category': cat,
                'units_sold': sold, 'revenue': revenue
            })

    # Expenses: mix of fixed shop-wide and variable per-category
    expense_rows = [
        {'category': 'SHOP', 'expense_type': 'Rent',        'amount': 1800.00},
        {'category': 'SHOP', 'expense_type': 'Utilities',   'amount': 240.00},
        {'category': 'SHOP', 'expense_type': 'Insurance',   'amount': 95.00},
        {'category': 'Clothing',    'expense_type': 'Steamer/Rail',  'amount': 25.00},
        {'category': 'Electronics', 'expense_type': 'PAT Testing',   'amount': 40.00},
        {'category': 'Furniture',   'expense_type': 'Delivery Fuel', 'amount': 60.00},
        {'category': 'SHOP', 'expense_type': 'Supplies/Bags', 'amount': 35.00},
    ]

    return (
        pd.DataFrame(sales_rows),
        pd.DataFrame(donation_rows),
        pd.DataFrame(expense_rows),
    )


# ─────────────────────────────────────────────────────────────────
#   QUICK TEXT REPORT (supplement to visual)
# ─────────────────────────────────────────────────────────────────

def print_text_report(model: CharityQPAM):
    df = model.factor_df_.reset_index()
    divider = "─" * 72

    print(f"\n{'═'*72}")
    print(f"  C-QPAM  ·  Axiom Capital Research  ·  Charity Allocation Report")
    print(f"{'═'*72}")

    print(f"\n{'FLOOR SPACE RECOMMENDATIONS':}")
    print(divider)
    top = df.sort_values('floor_allocation_pct', ascending=False)
    for _, r in top.iterrows():
        bar = '█' * int(r['floor_allocation_pct'] * 30)
        print(f"  {r['category']:<18} {bar:<30} {r['floor_allocation_pct']:>5.1%}  "
              f"({r['floor_sqft']:.0f} sqft)")

    print(f"\n{'PRICING SIGNALS':}")
    print(divider)
    for _, r in df.sort_values('score').iterrows():
        arrow = '▲' if 'PREMIUM' in r['pricing_signal'] else (
                '▼' if 'MARK' in r['pricing_signal'] or 'DIS' in r['pricing_signal'] else '=')
        print(f"  {r['category']:<18} {r['pricing_signal']:<16} "
              f"  Sell-through: {r['sellthrough']:.1%}   Score: {r['score']:+.3f}")

    print(f"\n{'BUDGET ALLOCATION (£{:.0f}/week)'.format(model.weekly_budget):}")
    print(divider)
    for _, r in df[df['budget_allocation']>0].sort_values('budget_allocation', ascending=False).iterrows():
        print(f"  {r['category']:<18} £{r['budget_allocation']:>7.2f}")

    print(f"\n{'VOLUNTEER HOURS ({:.0f} hrs/week)'.format(model.weekly_volunteer_hours):}")
    print(divider)
    for _, r in df.sort_values('volunteer_hours', ascending=False).iterrows():
        print(f"  {r['category']:<18} {r['volunteer_hours']:>5.1f} hrs")

    print(f"\n{'SUMMARY TABLE':}")
    print(divider)
    summary = df[['category', 'score', 'floor_allocation_pct', 'floor_sqft',
                  'budget_allocation', 'volunteer_hours', 'pricing_signal']].copy()
    summary.columns = ['Category', 'Score', 'Floor%', 'sqft', 'Budget£', 'Vol.Hrs', 'Signal']
    summary['Score'] = summary['Score'].map('{:+.3f}'.format)
    summary['Floor%'] = summary['Floor%'].map('{:.1%}'.format)
    print(summary.to_string(index=False))
    print(f"\n{'═'*72}\n")


# ─────────────────────────────────────────────────────────────────
#   MAIN — paste into a Jupyter cell or run as script
# ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':

    # 1. Generate dummy data
    sales_df, donations_df, expenses_df = generate_dummy_data(n_weeks=12)

    print("Sales data sample:")
    print(sales_df.head(10), "\n")

    # 2. Initialise and fit the model
    model = CharityQPAM(
        weights={'T': 0.4, 'D': 0.3, 'V': 0.3},
        total_floor_sqft=1200,
        weekly_budget=800,
        weekly_volunteer_hours=120,
    )
    model.fit(sales_df, donations_df, expenses_df)

    # 3. Text report
    print_text_report(model)

    # 4. Visual report (saves cqpam_report.png and displays inline in Jupyter)
    model.report(shop_name="British Heart Foundation – Chiswick Branch")
