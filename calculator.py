def calculate(a, op, b):
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "/":
        if b == 0:
            raise ZeroDivisionError("0으로 나눌 수 없습니다")
        return a / b
    raise ValueError(f"지원하지 않는 연산자: {op}")


def main():
    print("간단한 계산기 (종료: q)")
    while True:
        expr = input("입력 (예: 3 + 5): ").strip()
        if expr.lower() == "q":
            break
        parts = expr.split()
        if len(parts) != 3:
            print("형식이 올바르지 않습니다. 예: 3 + 5")
            continue
        a_str, op, b_str = parts
        try:
            a, b = float(a_str), float(b_str)
            result = calculate(a, op, b)
            print(f"결과: {result}")
        except ValueError as e:
            print(f"오류: {e}")
        except ZeroDivisionError as e:
            print(f"오류: {e}")


if __name__ == "__main__":
    main()
