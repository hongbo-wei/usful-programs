


# Stock Trader Flask App

本项目是一个基于 Flask 的股票交易演示应用，使用 Yahoo Finance 获取数据，SQLite 记录交易。


## 目录结构


```text
app.py                  # Flask 主入口
requirements.txt        # 依赖包
stock_trader/
    data.py             # 数据相关逻辑
    models/             # 数据模型
    services/           # 业务服务
    utils/              # 工具函数
    data/               # 数据库存放目录（trades.db 已移动至此）
templates/
    dashboard.html      # 可选的静态模板
```


## 运行方式


```bash
pip install -r requirements.txt
export FLASK_APP=app.py
flask run
```



## 说明

- 交易数据库文件已放在 `stock_trader/data/` 目录下，便于管理和备份。
- `.gitignore` 已配置忽略缓存和数据库文件。
- 如需添加测试，建议新建 `tests/` 目录。
