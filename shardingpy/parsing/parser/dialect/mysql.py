from shardingpy.constant import DatabaseType
from shardingpy.exception import SQLParsingException
from shardingpy.parsing.lexer.dialect.mysql import MySQLKeyword
from shardingpy.parsing.lexer.token import DefaultKeyword, Literals, Symbol
from shardingpy.parsing.parser.clauseparser import DistinctClauseParser, InsertIntoClauseParser, \
    InsertColumnsClauseParser, InsertValuesClauseParser, InsertSetClauseParser, InsertDuplicateKeyUpdateClauseParser, \
    UpdateSetItemsClauseParser
from shardingpy.parsing.parser.clauseparser import SelectListClauseParser, TableReferencesClauseParser, \
    WhereClauseParser, GroupByClauseParser, HavingClauseParser, OrderByClauseParser, SelectRestClauseParser
from shardingpy.parsing.parser.context.limit import Limit, LimitValue
from shardingpy.parsing.parser.expressionparser import AliasExpressionParser
from shardingpy.parsing.parser.sql.dml.delete import AbstractDeleteParser
from shardingpy.parsing.parser.sql.dml.insert import AbstractInsertParser
from shardingpy.parsing.parser.sql.dml.update import AbstractUpdateParser
from shardingpy.parsing.parser.sql.dql.select import AbstractSelectParser
from shardingpy.parsing.parser.token import OffsetToken, RowCountToken


class MySQLSelectClauseParserFacade:
    def __init__(self, sharding_rule, lexer_engine):
        self.distinct_clause_parser = MySQLDistinctClauseParser(lexer_engine)
        self.select_list_clause_parser = SelectListClauseParser(sharding_rule, lexer_engine)
        self.table_references_clause_parser = MySQLTableReferencesClauseParser(sharding_rule, lexer_engine)
        self.where_clause_parser = MySQLWhereClauseParser(lexer_engine)
        self.group_by_clause_parser = MySQLGroupByClauseParser(lexer_engine)
        self.having_clause_parser = HavingClauseParser(lexer_engine)
        self.order_by_clause_parser = OrderByClauseParser(lexer_engine)
        self.select_rest_clause_parser = MySQLSelectRestClauseParser(lexer_engine)


class MySQLSelectParser(AbstractSelectParser):
    def __init__(self, sharding_rule, lexer_engine):
        super().__init__(sharding_rule, lexer_engine, MySQLSelectClauseParserFacade(sharding_rule, lexer_engine))
        self.select_option_clause_parser = MySQLSelectOptionClauseParser(lexer_engine)
        self.limit_clause_parser = MySQLLimitClauseParser(lexer_engine)

    def parse_internal(self, select_statement):
        self.parse_distinct()
        self._parse_select_option()
        self.parse_select_list(select_statement, self.select_items)
        self.parse_from(select_statement)
        self.parse_where(self.sharding_rule, select_statement, self.select_items)
        self.parse_group_by(select_statement)
        self.parse_having()
        self.parse_order_by(select_statement)
        self._parse_limit(select_statement)
        self.parse_select_rest()

    def _parse_select_option(self):
        self.select_option_clause_parser.parse()

    def _parse_limit(self, select_statement):
        self.limit_clause_parser.parse(select_statement)


class MySQLDistinctClauseParser(DistinctClauseParser):
    def __init__(self, lexer_engine):
        self.lexer_engine = lexer_engine

    def get_synonymous_keywords_for_distinct(self):
        return []


class MySQLSelectOptionClauseParser:
    def __init__(self, lexer_engine):
        self.lexer_engine = lexer_engine

    def parse(self):
        self.lexer_engine.skip_all(MySQLKeyword.HIGH_PRIORITY, MySQLKeyword.STRAIGHT_JOIN,
                                   MySQLKeyword.SQL_SMALL_RESULT, MySQLKeyword.SQL_BIG_RESULT,
                                   MySQLKeyword.SQL_BUFFER_RESULT, MySQLKeyword.SQL_CACHE, MySQLKeyword.SQL_NO_CACHE,
                                   MySQLKeyword.SQL_CALC_FOUND_ROWS)


class MySQLTableReferencesClauseParser(TableReferencesClauseParser):
    def __init__(self, sharding_rule, lexer_engine):
        super().__init__(sharding_rule, lexer_engine)


class MySQLAliasExpressionParser(AliasExpressionParser):
    def __init__(self, lexer_engine):
        super().__init__(lexer_engine)

    def get_customized_available_keywords_for_table_alias(self):
        return [DefaultKeyword.LENGTH]


class MySQLWhereClauseParser(WhereClauseParser):
    def __init__(self, lexer_engine):
        super().__init__(DatabaseType.MySQL, lexer_engine)

    def get_customized_other_condition_operators(self):
        return [MySQLKeyword.REGEXP]


class MySQLGroupByClauseParser(GroupByClauseParser):
    def get_skipped_keyword_after_group_by(self):
        return [DefaultKeyword.WITH, MySQLKeyword.ROLLUP]


class MySQLLimitClauseParser:
    """
    [LIMIT {[offset,] row_count | row_count OFFSET offset}]
    """

    def __init__(self, lexer_engine):
        self.lexer_engine = lexer_engine

    def parse(self, select_satement):
        if not self.lexer_engine.skip_if_equal(MySQLKeyword.LIMIT):
            return
        value_index = -1
        value_begin_position = self.lexer_engine.get_current_token().end_position
        is_paramter_for_value = False
        if self.lexer_engine.equal_any(Literals.INT):
            value = int(self.lexer_engine.get_current_token().literals)
            value_begin_position = value_begin_position - len(str(value))
        elif self.lexer_engine.equal_any(Symbol.QUESTION):
            value_index = select_satement.parameters_index
            value = -1
            value_begin_position -= 1
            is_paramter_for_value = True
        else:
            raise SQLParsingException(self.lexer_engine)
        self.lexer_engine.next_token()
        if self.lexer_engine.skip_if_equal(Symbol.COMMA):
            select_satement.limit = self._get_limit_with_comma(value_index, value_begin_position, value,
                                                               is_paramter_for_value, select_satement)
            return
        if self.lexer_engine.skip_if_equal(MySQLKeyword.OFFSET):
            select_satement.limit = self._get_limit_with_offset(value_index, value_begin_position, value,
                                                                is_paramter_for_value, select_satement)
            return

        if is_paramter_for_value:
            select_satement.increase_parameters_index()
        else:
            select_satement.sql_tokens.append(RowCountToken(value_begin_position, value))

        select_satement.limit = Limit(DatabaseType.MySQL, None, LimitValue(value, value_index, False))

    def _get_limit_with_comma(self, index, value_begin_position, value, is_paramter_for_value, select_satement):
        row_count_begin_position = self.lexer_engine.get_current_token().end_position
        row_count_index = -1
        is_paramter_for_raw_count = False
        if self.lexer_engine.equal_any(Literals.INT):
            row_count_value = int(self.lexer_engine.get_current_token().literals)
            row_count_begin_position -= len(str(row_count_value))
        elif self.lexer_engine.equal_any(Symbol.QUESTION):
            row_count_index = select_satement.parameters_index if index == -1 else index + 1
            row_count_value = -1
            row_count_begin_position -= 1
            is_paramter_for_raw_count = True
        else:
            raise SQLParsingException(self.lexer_engine)
        self.lexer_engine.next_token()
        if is_paramter_for_value:
            select_satement.increase_parameters_index()
        else:
            select_satement.sql_tokens.append(OffsetToken(value_begin_position, value))
        if is_paramter_for_raw_count:
            select_satement.increase_parameters_index()
        else:
            select_satement.sql_tokens.append(RowCountToken(row_count_begin_position, row_count_value))
        return Limit(DatabaseType.MySQL, LimitValue(value, index, True),
                     LimitValue(row_count_value, row_count_index, False))

    def _get_limit_with_offset(self, index, value_begin_position, value, is_paramter_for_value, select_satement):
        offset_begin_position = self.lexer_engine.get_current_token().end_position
        offset_index = -1
        is_paramter_for_offset = False
        if self.lexer_engine.equal_any(Literals.INT):
            offset_value = int(self.lexer_engine.get_current_token().literals)
            offset_begin_position -= len(str(offset_value))
        elif self.lexer_engine.equal_any(Symbol.QUESTION):
            offset_index = select_satement.parameters_index if index == -1 else index + 1
            offset_value = -1
            offset_begin_position -= 1
            is_paramter_for_offset = True
        else:
            raise SQLParsingException(self.lexer_engine)
        self.lexer_engine.next_token()
        if is_paramter_for_offset:
            select_satement.increase_parameters_index()
        else:
            select_satement.sql_tokens.append(OffsetToken(offset_begin_position, offset_value))
        if is_paramter_for_value:
            select_satement.increase_parameters_index()
        else:
            select_satement.sql_tokens.append(RowCountToken(value_begin_position, value))
        return Limit(DatabaseType.MySQL, LimitValue(offset_value, offset_index, True),
                     LimitValue(value, index, False))


class MySQLSelectRestClauseParser(SelectRestClauseParser):
    def get_unsupported_keywords_rest(self):
        return [DefaultKeyword.PROCEDURE, DefaultKeyword.INTO]


class MySQLInsertClauseParserFacade:
    def __init__(self, sharding_rule, lexer_engine):
        self.insert_into_clause_parser = MySQLInsertIntoClauseParser(sharding_rule, lexer_engine)
        self.insert_columns_clause_parser = InsertColumnsClauseParser(sharding_rule, lexer_engine)
        self.insert_values_clause_parser = MySQLInsertValuesClauseParser(sharding_rule, lexer_engine)
        self.insert_set_clause_parser = MySQLInsertSetClauseParser(sharding_rule, lexer_engine)
        self.insert_duplicate_key_update_clause_parser = MySQLInsertDuplicateKeyUpateClauseParser(sharding_rule,
                                                                                                  lexer_engine)


class MySQLInsertParser(AbstractInsertParser):
    def __init__(self, sharding_rule, lexer_engine, sharding_meta_data):
        super().__init__(sharding_rule, sharding_meta_data, lexer_engine,
                         MySQLInsertClauseParserFacade(sharding_rule, lexer_engine))


class MySQLInsertIntoClauseParser(InsertIntoClauseParser):
    def __init__(self, sharding_rule, lexer_engine):
        super().__init__(lexer_engine, MySQLTableReferencesClauseParser(sharding_rule, lexer_engine))

    def get_skipped_keywords_between_table_and_values(self):
        return [MySQLKeyword.PARTITION]


class MySQLInsertValuesClauseParser(InsertValuesClauseParser):
    def get_synonymous_keywords_for_values(self):
        return [MySQLKeyword.VALUE]


class MySQLInsertSetClauseParser(InsertSetClauseParser):
    def get_customized_insert_keywords(self):
        return [DefaultKeyword.SET]


class MySQLInsertDuplicateKeyUpateClauseParser(InsertDuplicateKeyUpdateClauseParser):
    def get_customized_insert_keywords(self):
        return [DefaultKeyword.ON]


class MySQLUpdateClauseParserFacade:
    def __init__(self, sharding_rule, lexer_engine):
        self.table_references_clause_parser = MySQLTableReferencesClauseParser(sharding_rule, lexer_engine)
        self.update_set_items_clause_parser = UpdateSetItemsClauseParser(lexer_engine)
        self.where_clause_parser = MySQLWhereClauseParser(lexer_engine)


class MySQLUpdateParser(AbstractUpdateParser):
    def __init__(self, sharding_rule, lexer_engine):
        super().__init__(sharding_rule, lexer_engine, MySQLUpdateClauseParserFacade(sharding_rule, lexer_engine))

    def get_skipped_keywords_between_update_and_table(self):
        return [MySQLKeyword.LOW_PRIORITY, MySQLKeyword.IGNORE]


class MySQLDeleteClauseParserFacade:
    def __init__(self, sharding_rule, lexer_engine):
        self.table_references_clause_parser = MySQLTableReferencesClauseParser(sharding_rule, lexer_engine)
        self.where_clause_parser = MySQLWhereClauseParser(lexer_engine)


class MySQLDeleteParser(AbstractDeleteParser):
    def __init__(self, sharding_rule, lexer_engine):
        super().__init__(sharding_rule, lexer_engine, MySQLDeleteClauseParserFacade(sharding_rule, lexer_engine))

    def get_skipped_keywords_between_delete_and_table(self):
        return [MySQLKeyword.LOW_PRIORITY, MySQLKeyword.QUICK, MySQLKeyword.IGNORE, DefaultKeyword.FROM]
