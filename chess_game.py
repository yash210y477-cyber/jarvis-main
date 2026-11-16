# chess_game.py
import chess
import sys

def print_board(board):
    print(board)
    print()

def main():
    board = chess.Board()
    print("==== Welcome to Python Chess ====")
    print("Type moves in algebraic notation (e.g. e2e4, g1f3).")
    print("Type 'q' to quit.\n")
    print_board(board)

    while not board.is_game_over():
        try:
            input_text = input("Your move: ").strip()
            if input_text.lower() == 'q':
                print("Game quit.")
                sys.exit(0)

            # Parse move (e.g. "e2e4" or "e4")
            if len(input_text) == 2:
                san = input_text
            else:
                san = input_text

            # Try parsing as move
            try:
                move = board.parse_san(san)
            except ValueError:
                # If SAN fails, try UCI
                if len(input_text) == 4:
                    move = chess.Move.from_uci(input_text)
                else:
                    print("Invalid move