# -*- coding: utf-8 -*-
"""
数据迁移脚本：将原表数据迁移到优化的分区表

使用方法：
    python scripts/migrate_daily_data.py --source stock_daily_data --target stock_daily_data_partitioned
    python scripts/migrate_daily_data.py --verify  # 验证数据一致性
    python scripts/migrate_daily_data.py --swap  # 交换表名
"""

import pymysql
import argparse
import sys
from baostock_tool.config import get_db_config
from baostock_tool.utils.logger_utils import setup_logger
import time

db_config = get_db_config()
log_config = {
    "log_level": "INFO",
    "log_dir": "./logs"
}
logger = setup_logger(logger_name=__name__,
                      log_level=log_config["log_level"],
                      log_dir=log_config["log_dir"])


class DataMigrator:
    def __init__(self, db_config):
        self.db_config = db_config
        self.conn = None
        self.cursor = None

    def connect(self):
        """连接数据库"""
        try:
            self.conn = pymysql.connect(
                host=self.db_config['host'],
                port=self.db_config['port'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                database=self.db_config['database'],
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            self.cursor = self.conn.cursor()
            logger.info("数据库连接成功")
            return True
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return False

    def close(self):
        """关闭连接"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("数据库连接已关闭")

    def check_table_exists(self, table_name):
        """检查表是否存在"""
        try:
            sql = f"""
            SELECT COUNT(*) AS count
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = '{self.db_config['database']}'
              AND TABLE_NAME = '{table_name}'
            """
            self.cursor.execute(sql)
            result = self.cursor.fetchone()
            return result['count'] > 0
        except Exception as e:
            logger.error(f"检查表存在性失败: {e}")
            return False

    def get_table_count(self, table_name):
        """获取表记录数"""
        try:
            sql = f"SELECT COUNT(*) AS count FROM `{table_name}`"
            self.cursor.execute(sql)
            result = self.cursor.fetchone()
            return result['count']
        except Exception as e:
            logger.error(f"获取表记录数失败: {e}")
            return None

    def migrate_data(self, source_table, target_table, batch_size=100000):
        """
        分批迁移数据

        Args:
            source_table: 源表名
            target_table: 目标表名
            batch_size: 每批迁移的记录数
        """
        if not self.check_table_exists(source_table):
            logger.error(f"源表 {source_table} 不存在")
            return False

        if not self.check_table_exists(target_table):
            logger.error(f"目标表 {target_table} 不存在")
            return False

        # 获取源表总数
        source_count = self.get_table_count(source_table)
        if source_count is None:
            return False

        logger.info(f"源表 {source_table} 共有 {source_count} 条记录")

        # 获取目标表现有记录数
        target_count = self.get_table_count(target_table)
        logger.info(f"目标表 {target_table} 现有 {target_count} 条记录")

        if target_count >= source_count:
            logger.info("目标表记录数已 >= 源表，跳过迁移")
            return True

        # 计算剩余需要迁移的记录数
        remaining = source_count - target_count
        logger.info(f"需要迁移 {remaining} 条记录")

        # 使用INSERT INTO ... SELECT ... 一次性迁移（性能更好）
        try:
            start_time = time.time()

            # 迁移数据，按日期排序以避免锁等待
            sql = f"""
            INSERT INTO `{target_table}`
            SELECT * FROM `{source_table}`
            ORDER BY `date`, `market`, `code_int`, `frequency`
            """

            logger.info("开始迁移数据...")
            self.cursor.execute(sql)
            self.conn.commit()

            elapsed_time = time.time() - start_time
            logger.info(f"迁移完成！耗时 {elapsed_time:.2f} 秒")

            # 验证迁移结果
            new_target_count = self.get_table_count(target_table)
            logger.info(f"迁移后目标表记录数: {new_target_count}")

            if new_target_count == source_count:
                logger.info("数据迁移验证成功！")
                return True
            else:
                logger.warning(f"数据数量不一致: 源表{source_count}, 目标表{new_target_count}")
                return False

        except Exception as e:
            self.conn.rollback()
            logger.error(f"数据迁移失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def verify_data(self, source_table, target_table, sample_size=1000):
        """
        验证数据一致性

        Args:
            source_table: 源表名
            target_table: 目标表名
            sample_size: 采样检查数量
        """
        logger.info(f"开始验证数据一致性（采样 {sample_size} 条）...")

        try:
            # 随机采样比较
            sql = f"""
            SELECT s.*, t.date AS t_date
            FROM `{source_table}` s
            LEFT JOIN `{target_table}` t
              ON s.date = t.date
              AND s.market = t.market
              AND s.code_int = t.code_int
              AND s.frequency = t.frequency
            WHERE t.date IS NULL
            LIMIT 100
            """

            self.cursor.execute(sql)
            missing_records = self.cursor.fetchall()

            if missing_records:
                logger.error(f"发现 {len(missing_records)} 条在目标表中缺失的记录")
                return False
            else:
                logger.info("未发现缺失记录，采样验证通过")

            # 比较总数
            source_count = self.get_table_count(source_table)
            target_count = self.get_table_count(target_table)

            if source_count == target_count:
                logger.info(f"记录数一致: {source_count}")
                return True
            else:
                logger.error(f"记录数不一致: 源表{source_count}, 目标表{target_count}")
                return False

        except Exception as e:
            logger.error(f"数据验证失败: {e}")
            return False

    def swap_tables(self, old_table, new_table, backup_suffix='_backup'):
        """
        交换表名（安全切换）

        Args:
            old_table: 原表名
            new_table: 新表名
            backup_suffix: 备份表后缀
        """
        backup_table = f"{old_table}{backup_suffix}"

        try:
            # 步骤1: 将原表重命名为备份表
            logger.info(f"将 {old_table} 重命名为 {backup_table}...")
            self.cursor.execute(f"RENAME TABLE `{old_table}` TO `{backup_table}`")

            # 步骤2: 将新表重命名为原表名
            logger.info(f"将 {new_table} 重命名为 {old_table}...")
            self.cursor.execute(f"RENAME TABLE `{new_table}` TO `{old_table}`")

            self.conn.commit()
            logger.info("表名交换成功！")

            logger.info(f"旧表已备份为: {backup_table}")
            logger.info(f"新表已生效为: {old_table}")

            return True

        except Exception as e:
            self.conn.rollback()
            logger.error(f"表名交换失败: {e}")
            return False

    def analyze_table(self, table_name):
        """分析表并更新统计信息"""
        try:
            sql = f"ANALYZE TABLE `{table_name}`"
            self.cursor.execute(sql)
            result = self.cursor.fetchall()
            logger.info(f"表分析完成: {result[0]['Msg_text']}")
            return True
        except Exception as e:
            logger.error(f"表分析失败: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description='数据迁移工具')
    parser.add_argument('--source', default='stock_daily_data', help='源表名')
    parser.add_argument('--target', default='stock_daily_data_partitioned', help='目标表名')
    parser.add_argument('--migrate', action='store_true', help='执行数据迁移')
    parser.add_argument('--verify', action='store_true', help='验证数据一致性')
    parser.add_argument('--swap', action='store_true', help='交换表名')
    parser.add_argument('--analyze', action='store_true', help='分析表统计信息')
    parser.add_argument('--batch-size', type=int, default=100000, help='批次大小')

    args = parser.parse_args()

    migrator = DataMigrator(db_config)

    if not migrator.connect():
        sys.exit(1)

    try:
        if args.migrate:
            success = migrator.migrate_data(args.source, args.target, args.batch_size)
            if not success:
                logger.error("数据迁移失败")
                sys.exit(1)

        if args.verify:
            success = migrator.verify_data(args.source, args.target)
            if not success:
                logger.error("数据验证失败")
                sys.exit(1)

        if args.swap:
            success = migrator.swap_tables(args.source, args.target)
            if not success:
                logger.error("表名交换失败")
                sys.exit(1)

        if args.analyze:
            migrator.analyze_table(args.target)

        logger.info("操作完成")

    finally:
        migrator.close()


if __name__ == "__main__":
    main()
