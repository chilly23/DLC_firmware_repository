"""Decimal digit stepping without binary rounding drift."""
from decimal import Decimal,InvalidOperation

def digit_power(text,cursor,decimals):
    digits=[i for i,c in enumerate(text) if c.isdigit()]
    if not digits:return -decimals
    selected=min(digits,key=lambda i:abs(i-max(0,cursor-1)))
    dot=text.find('.')
    if dot<0:dot=len(text)
    return dot-selected-1 if selected<dot else dot-selected

def step_value(value,amount,power,minimum,maximum,decimals):
    try:
        current=Decimal(str(value));step=Decimal(10)**int(power)
        if not current.is_finite():raise InvalidOperation
        result=max(Decimal(str(minimum)),min(Decimal(str(maximum)),current+int(amount)*step))
        return f'{result:.{decimals}f}'
    except (InvalidOperation,ValueError,TypeError):raise ValueError('Enter a finite number before rotating.')

def cursor_for_power(text,power):
    dot=text.find('.')
    if dot<0:dot=len(text)
    index=dot-power-1 if power>=0 else dot-power
    digits=[i for i,c in enumerate(text) if c.isdigit()]
    return min(digits,key=lambda i:abs(i-index))+1 if digits else 0
