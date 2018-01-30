from __future__ import print_function
from .Game import GameRunner
from .Player import Room
from random import random, choice, shuffle


def create_room(gamedb, bot, compiler, size):
    stokens = gamedb.get_school_tokens()
    pool = []
    for stoken in stokens:
        pool += gamedb.get_tokens_for_school(stoken)

    if len(pool) == 0:
        from copy import deepcopy
        return Room([bot] + [deepcopy(bot) for _ in range(size - 1)])

    bots = [bot]
    while True:
        token = choice(pool)
        code, options = gamedb.get_code_and_options(token)
        try:
            prog = compiler.compile(code)
            prog.options = options
            bots += [prog]
            if len(bots) >= size:
                return Room(bots)
        except:
            print("Couldn't compile code for '{}' in '{}'".format(token, gamedb.get_school_for_token(token)))


def create_room_for_school(gamedb, stoken):
    # TODO: write this.
    raise Exception("Not Implemented!")


def avg(scores):
    return float((sum(scores) * 100) / len(scores)) / 100


def sim_competition(compiler, game, gamedb, token, runs, debug=False, score_func=avg):
    assert gamedb is not None
    assert gamedb.is_comp_token(token)

    seeds = [random() for _ in xrange(2 * runs + 5)]

    for school in gamedb.get_schools_in_comp(token):
        if debug:
            print("Got school '" + school + "'")
        max_score = 0
        max_code = ""
        for student in gamedb.get_tokens_for_school(school):
            if debug:
                print("got student '" + student + "'")
            code = gamedb.get_code(student)
            if not code:
                continue
            if debug:
                print("compiling code...")
            prog = compiler.compile(code.split("\n"))
            if debug:
                print("setting up game runner...")
            runner = gamerunner(game, prog)
            if debug:
                print("simulating...")
            score = none

            scores = []
            count = 0
            seed = 0
            # todo: make this able to run in a pool of threads (so it can be run on multiple cpus)
            while count < runs:
                try:
                    if seed >= len(seeds):
                        print("ran out of seeds")
                        break
                    scores += [runner.run_for_avg_score(times=1, seed=seeds[seed])]
                    # print(scores[-1])
                    # import sys
                    # sys.stdout.flush()
                    count += 1
                    seed += 1
                except exception as e:
                    print("there was an error simulating the game (moving to next seed):", e)
                    seed += 1
            score = score_func(scores)
            # score = runner.run_for_avg_score(times=runs)

            # while score is None:
            #     try:
            #     except Exception as e:
            #         print("There was an error simulating the game:", e)
            if score > max_score:
                max_score = score
                max_code = code
        if debug:
            print("Saving score...", max_score)
        gamedb.set_comp_avg_score(token, school, max_score)
        gamedb.set_comp_school_code(token, school, max_code)
    if debug:
        print("All done :)")


class Ranking(object):
    def __init__(self, bots):
        """

        Args:
            bots: Tuple containing standing and bot id
        """
        self.ranks = {}
        for i in range(0, len(bots)):
            self.ranks[bots[i]] = i #Key: BOTS Value: RANK

    def __add__(self, other):
        new_rank = {}
        for k in self.ranks:
            new_rank[k] = self.ranks[k] + other[k]
        return new_rank

    def __radd__(self, other):
        if other == 0:
            return self
        new_rank = {}
        for k in self.ranks:
            new_rank[k] = self.ranks[k] + other[k]
        return new_rank

    def add_rank(self, standing, bot):
        self.ranks[bot] += standing

class MultiplayerComp(object):
    RUN_FACTOR = 4

    def __init__(self, bots, room_size, default_bot_class):
        """

        Args:
            bots: (PROG) the players program to be executed and ranked
            room_size: (INT) the size of the rooms
        """
        self.default_bot_class = default_bot_class
        self.room_size = room_size
        self.scores = {}  # Bots:scores
        self.rooms = {}  # Rooms:Rankings
        self.cur_run = 0
        for bot in bots:
            self.scores[bot] = 0

    def __iter__(self):
        return self

    def __setitem__(self, key, value):
        """
        ARGS:
            key (Room): The room to set to ranking
            value (Ranking): The returned ranking
        """
        self.rooms[key] = value
        for k in value.ranks:
            if k in self.scores:
                self.scores[k] += value.ranks[k]
        # for bot in key.bots
        #     if bot in self.scores:
        #         self.scores[bot] += value.ranks[bot]


    def __next__(self):
        return self.next()

    def next(self):
        if self.cur_run == self.RUN_FACTOR:
            raise StopIteration()

        l = list(self.scores.keys())
        shuffle(l)
        p = l[:self.room_size + 1]
        while len(p) < self.room_size:
            p += [self.default_bot_class()]
        room = Room(p)
        self.rooms[room] = None
        self.cur_run += 1
        return room

    @staticmethod
    def sim_multiplayer(s_token, gamedb, game, compiler, debug=False):
        assert gamedb is not None
        assert gamedb.is_school_token(s_token)
        students = gamedb.get_tokens_for_school(s_token) #Only getting one school token
        bots = []
        for s in students:
            try:
                if debug:
                    print("got student '" + s +  "'")
                code = gamedb.get_code(s)
                if not code:
                    continue
                if debug:
                    print("compiling code...")
                prog = compiler.compile(code.split("\n"))
                if debug:
                    print("setting up game runner...")
                # runner = gamerunner(game, prog)
                if debug:
                    print("simulating...")
                bots += [prog]
            except:
                print("Couldn't compile code for '{}' in '{}'".format(s, gamedb.get_school_for_token(s_token)))
        tourney = MultiplayerComp(bots, 4, game.default_prog_for_computer())
        for room in tourney:
            print("Room: " + str(room))
            gamerunner = GameRunner(game, room)
            print(type(gamerunner))
            def add(x):
                return sum(x)
            tourney[room] = gamerunner.run_for_avg_score(times=1, func=add)

        for i in tourney.scores:
            print("Score {} for Bike: {}".format(tourney.scores[i], str(i)))
        return tourney.scores
