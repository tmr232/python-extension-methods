from square import get_square
from extend_4 import draw



def main():
    square = get_square()
    square.draw()

    # __getattr__ works
    print(square.snake)

    # But the naming is fragile
    draw = True
    try:
        square.draw()
    except AttributeError:
        print("So fragile!")


if __name__ == '__main__':
    main()
