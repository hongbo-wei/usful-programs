// 智能分析按钮逻辑
document.addEventListener('DOMContentLoaded', function() {
  var btn = document.getElementById('llm-analysis-btn');
  if (btn) {
    btn.addEventListener('click', function() {
      var loading = document.getElementById('llm-analysis-loading');
      var result = document.getElementById('llm-analysis-result');
      loading.style.display = '';
      result.style.display = 'none';
      fetch('/llm_analysis', {method: 'POST'})
        .then(r => r.json())
        .then(data => {
          loading.style.display = 'none';
          result.textContent = data.llm_answer || '无分析结果';
          result.style.display = '';
        })
        .catch(() => {
          loading.style.display = 'none';
          result.textContent = '分析失败';
          result.style.display = '';
        });
    });
  }
});
const marketData = {
    ...window.marketRows
};
const select = document.querySelector('select[name="symbol"]');
const priceDiv = document.getElementById('current-price');
function updatePrice() {
    const symbol = select.value;
    const price = marketData[symbol];
    priceDiv.innerHTML = price !== null ? `<i class='fa-solid fa-tag'></i> Current Price: <span class='fw-bold'>$${price}</span>` : '<i class="fa-solid fa-tag"></i> Current Price: <span class="text-danger">N/A</span>';
}
select.addEventListener('change', updatePrice);
updatePrice();
