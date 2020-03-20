# strikers: Queen, Rook, Bishop (less so)

import random
from reconchess import *
import chess.engine
import numpy as np


class MichaelBot(Player):
    # major methods taken from ReconChess docs (especially TroutBot)
    def __init__(self):
        self.board = None
        self.color = None
        self.my_piece_captured_square = None
        self.engine = chess.engine.SimpleEngine.popen_uci("stockfish_20011801_x64")

        self.turn_num = 0  # to be iterated for turn-based decisions
        self.piece_values = {1: 1, 2: 3, 3: 3.5, 4: 5, 5: 9, 6: 2}
        self.enemy_values = {1: 1, 2: 3, 3: 3.5, 4: 5, 5: 9, 6: 100}  # priorities for attacking
        self.game_state = 1  # to say if we need to attack quickly then retreat

    def handle_game_start(self, color: Color, board: chess.Board, opponent_name: str):
        self.board = board
        self.color = color
        print(self.color)

    def handle_opponent_move_result(self, captured_my_piece: bool, capture_square: Optional[Square]):
        self.my_piece_captured_square = capture_square
        if captured_my_piece:
            self.board.remove_piece_at(capture_square)

    def _get_my_pieces(self, move_actions):
        pt_dict = {'P': 1, 'N': 2, 'B': 3, 'R': 4, 'Q': 5, 'K': 6}

        # find all moves
        positions = []
        piece_types = []
        targets = []
        for i in move_actions:

            # find piece positions
            positions.append(i.from_square)
            # find piece targets (for deciding where to sense)
            targets.append(i.to_square)
            # find piece types
            piece_types.append(pt_dict[self.board.piece_at(i.from_square).symbol().upper()])
        piece_dict = {'position': positions, 'pieces': piece_types, 'targets': targets}
        return piece_dict

    def _calc_moves(self, piece_dict):
        # where I do Gillespie-esque decision making:

        priorities = []
        positions = piece_dict['position'].copy()
        if self.color == chess.BLACK:
            # position numbers are inverted
            positions = [64 - x for x in positions]
        distance_scores = [3 * int(x/8) for x in positions]  # weighting distance from the start
        centrality = [-1 * abs(4.5 - x % 8) for x in positions]  # weighting pieces near the center of the board
        piece_scores = [1.5*self.piece_values[p] for p in piece_dict['pieces']]
        total_score = [x + y + z for x, y, z in zip(distance_scores, piece_scores, centrality)]  # these may need to be fractions for random.choices
        idx_to_move = random.choices(range(len(piece_dict['position'])), weights=total_score)[0]
        piece_to_move = piece_dict['position'][idx_to_move]
        # can probably just find piece_to_move as before. idx_to_move may not be important. Leave as-is for now
        return piece_to_move

    def _find_target(self, piece_to_move, piece_dict):

        targets = piece_dict['targets']
        positions = piece_dict['position']
        idxs = [i for i, j in enumerate(positions) if j == piece_to_move] # getting indices of all possible moves
        my_targets = [targets[i] for i in idxs]

        # naive: just pick the largest distance (note - this will bias the right side of the board)
        # this models the aggressive side of the behavior - when using this policy, we can only move forward (as aggressively as possible)
        if self.color == chess.BLACK:
            target_dists = [(piece_to_move - i) for i in my_targets]
        elif self.color == chess.WHITE:
            target_dists = [(i - piece_to_move) for i in my_targets]
        max_target_idx = target_dists.index(max(target_dists))
        choice_target = my_targets[max_target_idx]
        return choice_target



    def choose_sense(self, sense_actions: List[Square], move_actions: List[chess.Move], seconds_left: float) -> \
            Optional[Square]:
        # return random.choice(sense_actions)
        #print('senses: ', sense_actions)
        #print('actions: ', (move_actions))
        #print(self._get_my_pieces(move_actions))
        #print(' ')
        #print(self._calc_moves(self._get_my_pieces(move_actions)))




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
        # Bounce between an aggressive policy (mine) and a conservative policy (Stockfish)

        # if we might be able to take the king, try to
        enemy_king_square = self.board.king(not self.color)
        if enemy_king_square:
            # if there are any ally pieces that can take king, execute one of those moves
            enemy_king_attackers = self.board.attackers(self.color, enemy_king_square)
            if enemy_king_attackers:
                attacker_square = enemy_king_attackers.pop()
                return chess.Move(attacker_square, enemy_king_square)

        ### my code here
        if self.game_state == 1:
            self.game_state *= -1
            piece_dict = self._get_my_pieces(move_actions)
            piece_to_move = self._calc_moves(piece_dict)
            target = self._find_target(piece_to_move, piece_dict)
            #self.game_state *= -1
            return chess.Move(piece_to_move, target)
        # otherwise, try to move with the stockfish chess engine
        elif self.game_state == -1:
            try:
                self.board.turn = self.color
                self.board.clear_stack()
                result = self.engine.play(self.board, chess.engine.Limit(time=0.5))
                self.game_state *= -1
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
