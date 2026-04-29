"""
配置文件：平台 URL、关键词、筛选阈值
"""

# Shopee 越南站
SHOPEE_VN_URL = "https://shopee.vn"
SHOPEE_SEARCH_URL = "https://shopee.vn/search"

# 1688
SOURCE_1688_URL = "https://s.1688.com"

# 拼多多（网页版）
PDD_URL = "https://mobile.yangkeduo.com"

# 越南语关键词 -> 中文关键词（用于跨平台匹配）
KEYWORDS = {
    "Ốp lưng điện thoại": "手机壳",
    "Cáp sạc điện thoại": "充电线",
    "Củ sạc điện thoại": "充电器",
    "Dán màn hình điện thoại": "手机膜",
    "Giá đỡ điện thoại": "手机支架",
    "Tai nghe điện thoại": "耳机",
    "Dây cáp sạc": "数据线",
    "Giá đỡ điện thoại trên ô tô": "车载支架",
}

# 价格筛选阈值：采购价 < Shopee售价 × PRICE_RATIO_THRESHOLD
PRICE_RATIO_THRESHOLD = 0.5

# 新手筛选条件
MIN_SHOPEE_SOLD = 100          # 最低已售数量（证明有需求）
MIN_RATING = 4.0               # 最低评分
MIN_REVIEW_COUNT = 20          # 最低评论数
MAX_SHOPEE_PRICE_VND = 300000  # Shopee 最高售价（越南盾），新手建议低客单价
MIN_PROFIT_MARGIN = 0.50       # 最低利润率 50%

# Playwright CDP 连接
CDP_HOST = "localhost"
CDP_PORT = 9222
