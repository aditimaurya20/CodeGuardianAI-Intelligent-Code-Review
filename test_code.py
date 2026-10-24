def calculate_result(numbers):
    total = 0
    for number in numbers:
        if number > 0:
            if number % 2 == 0:
                total += number
            else:
                total += number * 2
        elif number < 0:
            total -= number
        else:
            total = total + 0
    return total