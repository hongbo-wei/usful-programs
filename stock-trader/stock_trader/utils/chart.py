import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend for server environments
import matplotlib.pyplot as plt
import io
import base64

def generate_asset_bar_chart(stock_buy, stock_market, crypto_buy, crypto_market):
    labels = ["Stock", "Crypto"]
    buy_values = [stock_buy, crypto_buy]
    market_values = [stock_market, crypto_market]
    fig, ax = plt.subplots(figsize=(6, 3.5), dpi=120)
    bar_width = 0.35
    x = range(len(labels))
    buy_colors = ["#6EC6FF", "#FFD54F"]
    market_colors = ["#AB47BC", "#4DB6AC"]
    ax.bar(x, buy_values, bar_width, label="Buy Total", color=buy_colors, edgecolor="#fff", linewidth=1.5)
    ax.bar([i + bar_width for i in x], market_values, bar_width, label="Market Value", color=market_colors, edgecolor="#fff", linewidth=1.5)
    ax.set_xticks([i + bar_width / 2 for i in x])
    ax.set_xticklabels(labels, fontsize=13, fontweight="bold")
    ax.set_ylabel("USD", fontsize=12)
    ax.set_title("Buy Total vs Market Value", fontsize=15, fontweight="bold", color="#195ca7")
    ax.legend(fontsize=11, loc="upper right", frameon=False)
    ax.grid(axis="y", linestyle="--", alpha=0.18)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    # 在柱状图上方添加百分比
    for i, (buy, market) in enumerate(zip(buy_values, market_values)):
        percent = (market / buy * 100) if buy else 0
        ax.text(i + bar_width/2, max(buy, market) * 1.02, f"{percent:.2f}%", ha='center', fontsize=11, color="#195ca7", fontweight="bold")
    fig.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", transparent=True)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()

def generate_position_pie_chart(position_rows):
    """
    生成持仓分布饼图，输入为position_rows（每项需有'Symbol'和'Market Value'）。
    返回base64编码的PNG图片。
    """
    if not position_rows:
        return None
    labels = [row['Symbol'] for row in position_rows]
    sizes = [row['Market Value'] for row in position_rows]
    if not any(sizes):
        return None
    fig, ax = plt.subplots(figsize=(3.5,3.5), dpi=120)
    colors = plt.cm.Paired(range(len(labels)))
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, autopct='%1.1f%%', startangle=140,
        colors=colors, textprops={'fontsize':9, 'color':'#222'}, wedgeprops={'edgecolor':'#fff', 'linewidth':1.5, 'alpha':0.95}
    )
    ax.set_title('Position Distribution', fontsize=13, fontweight='bold', color='#195ca7')
    plt.setp(autotexts, size=9, weight='bold', color='#195ca7')
    ax.axis('equal')
    fig.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', transparent=True)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()
