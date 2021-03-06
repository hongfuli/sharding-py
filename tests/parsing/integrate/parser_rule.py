sharding_rule_config = {
    'data_sources': {
        'ds0': None,
        'ds1': None
    },
    'sharding_rule': {
        'tables': {
            't_order': {
                'actual_data_nodes': ['ds0.t_order', 'ds1.t_order'],
                'table_strategy': {
                    'complex': {
                        'sharding_columns': ['user_id', 'order_id'],
                        'algorithm_class_name': 'tests.api.algorithm.fixture.TestComplexKeysShardingAlgorithm'
                    }
                },
                'logic_index': 'order_index'
            },
            't_order_item': {
                'actual_data_nodes': ['ds0.t_order_item', 'ds1.t_order_item'],
                'table_strategy': {
                    'complex': {
                        'sharding_columns': ['user_id', 'order_id', 'item_id'],
                        'algorithm_class_name': 'tests.api.algorithm.fixture.TestComplexKeysShardingAlgorithm'
                    }
                },
                'key_generator_column_name': 'item_id',
                'key_generator_class_name': 'shardingpy.keygen.base.DefaultKeyGenerator',
            },
            't_place': {
                'actual_data_nodes': ['db0.t_place', 'db1.t_place'],
                'table_strategy': {
                    'complex': {
                        'sharding_columns': ['user_new_id', 'guid'],
                        'algorithm_class_name': 'tests.api.algorithm.fixture.TestComplexKeysShardingAlgorithm'
                    }
                }
            }
        },
        'binding_tables': [('t_order', 't_order_item')],
        'default_key_generator': None
    }
}
