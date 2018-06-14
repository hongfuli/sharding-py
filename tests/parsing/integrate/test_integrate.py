import unittest

from shardingpy.api.config.base import load_sharding_rule_config_from_dict
from shardingpy.constant import DatabaseType
from shardingpy.metadata.base import ShardingMetaData, TableMetaData, ColumnMetaData
from shardingpy.parsing.parser.parser_engine import SQLParsingEngine
from shardingpy.rule.base import ShardingRule
from .asserts.base import get_parser_result
from . import parser_rule
from .. import sql as sql_cases_loader


class IntegrateSupportedSQLParsingTestCase(unittest.TestCase):

    def test_supported_sqls(self):
        for sql_case_id, database_type, sql_case_type in sql_cases_loader.get_supported_sql_test_parameters(
                [DatabaseType.MySQL, DatabaseType.H2]):
            self.assert_supported_sql(sql_case_id, database_type, sql_case_type)

    def assert_supported_sql(self, sql_case_id, database_type, sql_case_type):
        print("test: {} - {} - {}".format(sql_case_id, database_type.name, sql_case_type.name))
        sql = sql_cases_loader.get_supported_sql(sql_case_id, sql_case_type,
                                                 get_parser_result(sql_case_id).get('parameters'))
        SQLParsingEngine(database_type, sql, self.get_sharding_rule(), self.get_sharding_meta_data())

    def get_sharding_rule(self):
        sharding_rule_config = load_sharding_rule_config_from_dict(parser_rule.sharding_rule_config['sharding_rule'])
        return ShardingRule(sharding_rule_config, parser_rule.sharding_rule_config['data_sources'].keys())

    def get_sharding_meta_data(self):
        sharding_meta_data = ShardingMetaData()
        table_meta_data_map = dict()
        table_meta_data_map['t_order'] = self.get_table_meta_data(['order_id', 'user_id'])
        table_meta_data_map['t_order_item'] = self.get_table_meta_data(
            ['item_id', 'order_id', 'user_id', 'status', 'c_date'])
        table_meta_data_map['t_place'] = self.get_table_meta_data(['order_id', 'user_id'])
        return sharding_meta_data

    def get_table_meta_data(self, column_names):
        return TableMetaData([ColumnMetaData(cn, 'int(11)', '') for cn in column_names])
