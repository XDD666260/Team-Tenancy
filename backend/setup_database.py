# 数据库初始化脚本
# 创建 secondhouse_cq 数据库及所有表结构

import pymysql

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',
    'charset': 'utf8mb4',
}

def create_database():
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS secondhouse_cq DEFAULT CHARSET utf8mb4")
    print("✅ 数据库 secondhouse_cq 已就绪")
    cursor.close()
    conn.close()

def create_tables():
    DB_CONFIG['database'] = 'secondhouse_cq'
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # ========== 房源主表 ==========
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS houses (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            title VARCHAR(300) COMMENT '房源标题',
            district VARCHAR(50) COMMENT '区县',
            biz_circle VARCHAR(50) COMMENT '商圈',
            community VARCHAR(100) COMMENT '小区名称',
            address VARCHAR(300) COMMENT '详细地址',
            total_price DECIMAL(12,2) COMMENT '总价（万）',
            unit_price DECIMAL(10,2) COMMENT '单价（元/㎡）',
            area DECIMAL(8,2) COMMENT '面积（㎡）',
            layout VARCHAR(20) COMMENT '户型原文',
            rooms INT COMMENT '室',
            halls INT COMMENT '厅',
            bathrooms INT COMMENT '卫',
            floor_desc VARCHAR(50) COMMENT '楼层描述原文',
            floor_type VARCHAR(10) COMMENT '低层/中层/高层',
            total_floors INT COMMENT '总楼层',
            orientation VARCHAR(20) COMMENT '朝向',
            decoration VARCHAR(20) COMMENT '装修',
            build_year INT COMMENT '建成年代',
            lng DECIMAL(10,6) COMMENT '经度',
            lat DECIMAL(10,6) COMMENT '纬度',
            followers INT DEFAULT 0 COMMENT '关注人数',
            source VARCHAR(20) COMMENT '数据来源: lianjia/anjuke',
            source_id VARCHAR(100) COMMENT '原始来源ID',
            fingerprint VARCHAR(64) COMMENT '去重指纹(MD5)',
            status VARCHAR(20) DEFAULT 'on_sale' COMMENT '状态: on_sale/sold/offline',
            first_seen DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '首次发现时间',
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',

            INDEX idx_district (district),
            INDEX idx_biz_circle (biz_circle),
            INDEX idx_total_price (total_price),
            INDEX idx_unit_price (unit_price),
            INDEX idx_source (source),
            INDEX idx_status (status),
            UNIQUE INDEX idx_fingerprint (fingerprint)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='二手房房源表'
    """)
    print("✅ 表 houses 已就绪")

    # ========== 爬取日志表 ==========
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS crawl_log (
            id INT PRIMARY KEY AUTO_INCREMENT,
            source VARCHAR(20) COMMENT '数据来源',
            district VARCHAR(50) COMMENT '区县',
            page INT COMMENT '页码',
            houses_found INT DEFAULT 0 COMMENT '本页发现房源数',
            new_added INT DEFAULT 0 COMMENT '新增数量',
            updated INT DEFAULT 0 COMMENT '更新数量',
            status VARCHAR(20) COMMENT 'success/failed',
            message TEXT COMMENT '备注信息',
            crawl_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '爬取时间',

            INDEX idx_source (source),
            INDEX idx_crawl_time (crawl_time)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='爬取日志'
    """)
    print("✅ 表 crawl_log 已就绪")

    # ========== 分析结果表 ==========
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analysis_results (
            id INT PRIMARY KEY AUTO_INCREMENT,
            analysis_type VARCHAR(50) COMMENT '分析类型: prediction/clustering/rules',
            result_data JSON COMMENT '分析结果JSON',
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP,

            INDEX idx_type (analysis_type),
            INDEX idx_create_time (create_time)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='分析结果缓存'
    """)
    print("✅ 表 analysis_results 已就绪")

    conn.commit()
    cursor.close()
    conn.close()
    print("\n🎉 数据库初始化完成！")


if __name__ == '__main__':
    create_database()
    create_tables()
