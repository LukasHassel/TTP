from itertools import batched
from math import inf
from helpers import *
from collections import Counter
from pprint import pp
from tqdm import tqdm
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor
import datetime

@dataclass
class Statistic:
    n : int = 0
    accumulator : int = 0
    maximum : int = 0
    minimum : int = inf

    def record(self, value):
        self.accumulator += value
        self.minimum = min(self.minimum, value)
        self.maximum = max(self.maximum, value)
        self.n += 1
    
    def __str__(self):
        return "average: {}, minimum: {}, maximum: {}".format(*self.evaluate())

    def evaluate(self):
        return self.accumulator / self.n, self.minimum, self.maximum

class Experiment:

    def __init__(self, repetitions=1_000_000, nTeams=2, maxStreak=3, timeCreated:datetime.datetime=datetime.datetime.now()) -> None: 
        self.NREPETITIONS = repetitions
        self.NTEAMS = nTeams
        self.NROUNDS = 2 * (self.NTEAMS-1)
        self.NGAMES = self.NTEAMS * (self.NTEAMS-1)
        self.NGAMESPERROUND = self.NGAMES // self.NROUNDS
        self.MAXSTREAK = maxStreak
        self.doubleRoundRobinViolations  = Statistic()
        self.maxStreakViolations         = Statistic()
        self.noRepeatViolations          = Statistic()
        self.timeCreated = timeCreated

    def gameIdToTeamIds(self, gid):
        host = gid // (self.NTEAMS-1)
        guest = gid % (self.NTEAMS-1)
        if guest >= host:
            guest += 1
        return host, guest

    def teamIdsToGameId(self, host, guest):
        gid = host * (self.NTEAMS - 1) + guest
        if guest > host:
            gid -= 1
        return gid

    # This function generates a random round for the tournament, with no repeats of teams in adjacent games.
    def randomRound(self):
        teamIds = list(range(self.NTEAMS))
        shuffledTeamIds = shuffled(teamIds)
        return sorted(list(map(lambda t: self.teamIdsToGameId(*t), batched(shuffledTeamIds, 2))))

    def randomTournament(self): 
        return [[self.gameIdToTeamIds(gid) for gid in self.randomRound()] for _ in range(self.NROUNDS)]

    def countDoubleRoundRobinViolations(self, tournament):
        counter = Counter(flatten(tournament))
        violations = 0
        for host in range(self.NTEAMS):
            for guest in range(host+1, self.NTEAMS): # Only check every pair once
                violations += abs(1-counter[(host, guest)])
                violations += abs(1-counter[(guest, host)])
        return violations

    def countNoRepeatViolations(self, tournament):
        violations = 0
        for nextRoundNr in range(1, self.NROUNDS):
            currentRoundNr = nextRoundNr-1
            nextRound = tournament[nextRoundNr]
            currentRound = tournament[currentRoundNr]
            for (host, guest) in currentRound:
                if (host, guest) in nextRound:
                    violations+=1
                if (guest, host) in nextRound:
                    violations+=1
        return violations

    def countMaxStreakViolations(self, tournament):
        violations = 0
        streak = {team:(0,0) for team in range(self.NTEAMS)}
        for round in tournament:
            for (host, guest) in round:
                home, away = streak[host]
                if home+1 > self.MAXSTREAK:
                    violations+=1
                streak[host]=(home+1, 0)
                home, away = streak[guest]
                if away+1 > self.MAXSTREAK:
                    violations+=1
                streak[guest]=(0, away+1)
        return violations
    
    def execute(self):
        for repetition in tqdm(range(self.NREPETITIONS), desc="teams:{}".format(self.NTEAMS)):
            tournament = self.randomTournament()
            self.doubleRoundRobinViolations.record(
                self.countDoubleRoundRobinViolations(tournament)
            )
            self.maxStreakViolations.record(
                self.countMaxStreakViolations(tournament)
            )
            self.noRepeatViolations.record(
                self.countNoRepeatViolations(tournament)
            )
        self.saveResults()

    def saveResults(self):
        with open("{}-{}teams-{}reps.txt".format(self.timeCreated.strftime("%Y%m%d-%H:%M"), self.NTEAMS, self.NREPETITIONS), "w") as file:
            print("Double Round Robin Violations",self.doubleRoundRobinViolations,file=file)
            print("Maximum Streak Violations",self.maxStreakViolations,file=file)
            print("No Repeat Violations",self.noRepeatViolations,file=file)

def executeExperiment(exp:Experiment):
    random.seed(1)
    exp.execute()
    return exp

def main():
    time = datetime.datetime.now()
    pool = ProcessPoolExecutor()
    experiments = [Experiment(repetitions=1_000_000, nTeams=nTeams, timeCreated=time) for nTeams in range(4, 52, 2)]
    experiments = pool.map(executeExperiment, experiments)
    pool.shutdown()
    for exp in experiments:
        print(exp.timeCreated,"Double Round Robin Violations",exp.doubleRoundRobinViolations,"\nMaximum Streak Violations",exp.maxStreakViolations,"\nNo Repeat Violations",exp.noRepeatViolations)

if __name__ == "__main__":
    main()