import smart_imports

smart_imports.all()


class Restrictions:
    __slots__ = ('hard_minimum', 'hard_maximum', 'soft_minimum', 'soft_maximum')

    def __init__(self, hard_minimum=0, hard_maximum=None, soft_minimum=None, soft_maximum=None):
        self.hard_minimum = hard_minimum
        self.hard_maximum = hard_maximum
        self.soft_minimum = soft_minimum
        self.soft_maximum = soft_maximum

    def serialize(self):
        return {'hard_minimum': self.hard_minimum,
                'hard_maximum': self.hard_maximum,
                'soft_minimum': self.soft_minimum,
                'soft_maximum': self.soft_maximum}

    @classmethod
    def deserialize(cls, data):
        return cls(**data)

    def __eq__(self, other):
        return (self.__class__ == other.__class__ and
                all(getattr(self, field) == getattr(other, field) for field in self.__slots__))

    def __ne__(self, other):
        return not self.__eq__(other)


class Client(client.Client):
    __slots__ = ('transaction_lifetime',)

    Restrictions = Restrictions

    def __init__(self, transaction_lifetime, **kwargs):
        super().__init__(**kwargs)
        self.transaction_lifetime = transaction_lifetime

    def cmd_balances(self, accounts_ids):
        answer = operations.sync_request(url=self.url('accounts/balances'),
                                         data=tt_protocol_bank_pb2.AccountsBalancesRequest(accounts_ids=tuple(accounts_ids)),
                                         AnswerType=tt_protocol_bank_pb2.AccountsBalancesResponse)

        return {account_id: dict(balances.amounts)
                  for account_id, balances in answer.balances.items()}

    def cmd_balance(self, account_id, currency=None):
        if isinstance(currency, int):
            pass
        elif currency is None:
            currency = 0
        else:
            currency = currency.value

        return self.cmd_balances(accounts_ids=(account_id,))[account_id].get(currency, 0)

    def cmd_change_balance(self,
                           account_id,
                           type,
                           amount,
                           asynchronous=False,
                           autocommit=False,
                           currency=None,
                           restrictions=Restrictions(),
                           transaction_lifetime=None):

        if transaction_lifetime is None:
            transaction_lifetime = self.transaction_lifetime

        if isinstance(currency, int):
            pass
        elif currency is None:
            currency = 0
        else:
            currency = currency.value

        if asynchronous and not autocommit:
            raise exceptions.AutocommitRequiredForAsyncTransaction

        applied_operations = [tt_protocol_bank_pb2.Operation(account_id=account_id,
                                                             currency=currency,
                                                             amount=amount,
                                                             type=type)]

        restrictions = s11n.to_json(restrictions.serialize())

        if not asynchronous:
            try:
                answer = operations.sync_request(url=self.url('transactions/start'),
                                                 data=tt_protocol_bank_pb2.StartTransactionRequest(lifetime=transaction_lifetime,
                                                                                                   operations=applied_operations,
                                                                                                   autocommit=autocommit,
                                                                                                   restrictions=restrictions),
                                                 AnswerType=tt_protocol_bank_pb2.StartTransactionResponse)
            except exceptions.TTAPIUnexpectedAPIStatus:
                return False, None

            return True, answer.transaction_id

        operations.async_request(url=self.url('transactions/start'),
                                 data=tt_protocol_bank_pb2.StartTransactionRequest(lifetime=transaction_lifetime,
                                                                                   operations=applied_operations,
                                                                                   autocommit=autocommit,
                                                                                   restrictions=restrictions))

        return True, None

    def cmd_commit_transaction(self, transaction_id):
        operations.async_request(url=self.url('transactions/commit'),
                                 data=tt_protocol_bank_pb2.CommitTransactionRequest(transaction_id=transaction_id))

    def cmd_rollback_transaction(self, transaction_id):
        operations.async_request(url=self.url('transactions/rollback'),
                                 data=tt_protocol_bank_pb2.RollbackTransactionRequest(transaction_id=transaction_id))

    def cmd_debug_clear_service(self):
        if not django_settings.TESTS_RUNNING:
            return

        operations.sync_request(url=self.url('debug-clear-service'),
                                data=tt_protocol_bank_pb2.DebugClearServiceRequest(),
                                AnswerType=tt_protocol_bank_pb2.DebugClearServiceResponse)

    def banker(self, change_balance_error, currency=None):

        @contextlib.contextmanager
        def points_transaction(account_id, type, amount):
            success, transaction_id = self.cmd_change_balance(account_id=account_id,
                                                              type=type,
                                                              amount=amount,
                                                              asynchronous=False,
                                                              autocommit=False,
                                                              currency=currency)

            if not success:
                raise change_balance_error()

            with self.commit_or_rollback(transaction_id):
                yield

        return points_transaction

    @contextlib.contextmanager
    def commit_or_rollback(self, transaction_id):
        try:
            yield
        except Exception:
            self.cmd_rollback_transaction(transaction_id)
            raise
        else:
            self.cmd_commit_transaction(transaction_id)
