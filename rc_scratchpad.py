# strikers: Queen, Rook, Bishop (less so)

import random
from reconchess import *
import chess
import numpy as np

class MichaelBot(Player):
    # major methods taken from ReconChess docs (especially TroutBot)
    def __init__(self):
        self.board = None
        self.color = None
        self.my_piece_captured_square = None

        self.turn_num = 0  # to be iterated for turn-based decisions
        self.piece_values = {1: 1, 2: 3, 3: 3.5, 4: 5, 5: 9}
        self.enemy_values = {1: 1, 2: 3, 3: 3.5, 4: 5, 5: 9, 6: 100}  # priorities for attacking
        self.in_out_timer = 0  # to say if we need to attack quickly then retreat

    def handle_game_start(self, color: Color, board: chess.Board, opponent_name: str):
        self.board = board
        self.color = color

    def handle_opponent_move_result(self, captured_my_piece: bool, capture_square: Optional[Square]):
        self.my_piece_captured_square = capture_square
        if captured_my_piece:
            self.board.remove_piece_at(capture_square)

    def _get_my_pieces(self):
        self.current_pieces = {i: [] for i in range(1, 7)}

        for piece_type in range(1, 7):
            for pos in self.board.pieces(piece_type, self.color):
                current_pieces = current_pieces[piece_type].append(pos)

    def _calc_moves(self):
        # where I do Gillespie-esque decision making
        piece_dict = self.current_pieces
        priority_dict = self.piece_dict.copy()
        for k in priority_dict.keys():
            if self.color == chess.BLACK:
                # numbers are inverted
                priority_dict[k] = [64 - x for x in priority_dict[k]]
            priority_dict[k] += 3 * [int(x) for x in priority_dict[k]] # prioritizing distance
            priority_dict[k] += self.piece_values[k]

        piece_to_move = **place with max value**
        return piece_to_move
            # priority_dict[k] += ***distance from baseline so pieces farther away get chosen



    def choose_sense(self, sense_actions: List[Square], move_actions: List[chess.Move], seconds_left: float) -> \
            Optional[Square]:
        # return random.choice(sense_actions)

        # if we might capture a piece when we move, sense where the capture will occur
        future_move = self.choose_move(move_actions, seconds_left)
        if future_move is not None and self.board.piece_at(future_move.to_square) is not None:
            return future_move.to_square

        # otherwise, just randomly choose a sense action, but don't sense on a square where our pieces are located
        for square, piece in self.board.piece_map().items():
            if piece.color == self.color:
                sense_actions.remove(square)
        return random.choice(sense_actions)

    def handle_sense_result(self, sense_result: List[Tuple[Square, Optional[chess.Piece]]]):
        # add the pieces in the sense result to our board
        for square, piece in sense_result:
            self.board.set_piece_at(square, piece)

    def choose_move(self, move_actions: List[chess.Move], seconds_left: float) -> Optional[chess.Move]:
        # return random.choice(move_actions + [None])
        # if we might be able to take the king, try to
        enemy_king_square = self.board.king(not self.color)
        if enemy_king_square:
            # if there are any ally pieces that can take king, execute one of those moves
            enemy_king_attackers = self.board.attackers(self.color, enemy_king_square)
            if enemy_king_attackers:
                attacker_square = enemy_king_attackers.pop()
                return chess.Move(attacker_square, enemy_king_square)

        # otherwise, try to move with the stockfish chess engine
        try:
            self.board.turn = self.color
            self.board.clear_stack()
            result = self.engine.play(self.board, chess.engine.Limit(time=0.5))
            return result.move
        except chess.engine.EngineTerminatedError:
            print('Stockfish Engine died')
        except chess.engine.EngineError:
            print('Stockfish Engine bad state at "{}"'.format(self.board.fen()))

        # if all else fails, pass
        return None

    def handle_move_result(self, requested_move: Optional[chess.Move], taken_move: Optional[chess.Move],
                           captured_opponent_piece: bool, capture_square: Optional[Square]):
        # if a move was executed, apply it to our board
        if taken_move is not None:
            self.board.push(taken_move)

    def handle_game_end(self, winner_color: Optional[Color], win_reason: Optional[WinReason],
                        game_history: GameHistory):
        try:
            # if the engine is already terminated then this call will throw an exception
            self.engine.quit()
        except chess.engine.EngineTerminatedError:
            pass
