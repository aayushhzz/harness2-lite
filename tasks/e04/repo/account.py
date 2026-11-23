class InsufficientFunds(Exception):
    pass


class Account:
    def __init__(self, balance=0):
        self.balance = balance

    def deposit(self, amount):
        self.balance += amount
        return self.balance

    def withdraw(self, amount):
        if amount >= self.balance:
            raise InsufficientFunds("not enough money")
        self.balance -= amount
        return self.balance
