#!/usr/bin/env python

# ant.py
# Eric Rollins 2008

#   This program generates a random array of distances between cities, then uses
#   Ant Colony Optimization to find a short path traversing all the cities --
#   the Travelling Salesman Problem.
#
#   In this version of Ant Colony Optimization each ant starts in a random city.
#   Paths are randomly chosed with probability inversely proportional to to the
#   distance to the next city.  At the end of its travel the ant updates the
#   pheromone matrix with its path if this path is the shortest one yet found.
#   The probability of later ants taking a path is increased by the pheromone
#   value on that path.  Pheromone values evaporate (decrease) over time.
#
#   In this impementation weights between cities actually represent
#   (maxDistance - dist), so we are trying to maximize the score.
#
#   Usage: ant seed boost iterations cities
#     seed         seed for random number generator (1,2,3...).
#                  This seed controls the city distance array.  Remote
#                  executions have their seed values fixed (1,2) so each will
#                  produce a different result.
#     boost        pheromone boost for best path.  5 appears good.
#                  0 disables pheromones, providing random search.
#     iterations   number of ants to be run.
#     cities       number of cities.

import random
import time

from tpy import copy, Int32, Own

# type Matrix = Array[Array[double]]
# type Path = List[int]
# type CitySet = HashSet[int]

# int * int * int -> Matrix
def randomMatrix(n: Int32, upperBound: Int32, seed: Int32) -> Own[list[list[float]]]:
    random.seed(seed)
    m: list[list[float]] = []
    for r in range(n):
        # The original appends sm to m and *then* fills it, relying on CPython
        # aliasing the same list. TurboPython containers own what they store, so
        # the row is filled first and appended once complete -- same result in
        # both runtimes.
        sm: list[float] = []
        for c in range(n):
             sm.append(upperBound * random.random())
        m.append(sm)
    return m

# Path -> Path
def wrappedPath(path: list[Int32]) -> Own[list[Int32]]:
    # path[1:] is a non-owning Span in TurboPython, so it cannot be concatenated;
    # the rotated copy is built directly.
    out = [path[i] for i in range(1, len(path))]
    out.append(path[0])
    return out

# Matrix * Path -> double
def pathLength(cities: list[list[float]], path: list[Int32]) -> float:
    pairs = list(zip(path, wrappedPath(path)))
    # Neumaier compensated summation, spelled out. CPython's sum() has used it
    # for floats since 3.12; TurboPython's sum() accumulates naively, and the
    # resulting one-ULP difference flips the `pathLen > bestLen` test and
    # changes which tour the search keeps -- so this is not cosmetic.
    total = 0.0
    comp = 0.0
    for (r, c) in pairs:
        x = cities[r][c]
        t = total + x
        if abs(total) >= abs(x):
            comp += (total - t) + x
        else:
            comp += (x - t) + total
        total = t
    return total + comp

# Boosts pheromones for cities on path.
# Matrix * Path * int -> unit
def updatePher(pher: list[list[float]], path: list[Int32], boost: Int32) -> None:
    pairs = list(zip(path, wrappedPath(path)))
    for (r,c) in pairs:
        pher[r][c] = pher[r][c] + boost

# Matrix * int * int -> unit
def evaporatePher(pher: list[list[float]], maxIter: Int32, boost: Int32) -> None:
    decr = boost / float(maxIter)
    for r in range(len(pher)):
        for c in range(len(pher[r])):
            if pher[r][c] > decr:
                pher[r][c] = pher[r][c] - decr
            else:
                pher[r][c] = 0.0

# Sum weights for all paths to cities adjacent to current.
# Matrix * Matrix * CitySet * int -> double
def doSumWeight(cities: list[list[float]], pher: list[list[float]],
                used: dict[Int32, Int32], current: Int32) -> float:
    runningTotal = 0.0
    for city in range(len(cities)):
        if city not in used:
            runningTotal = (runningTotal +
                            cities[current][city] * (1.0 + pher[current][city]))
    return runningTotal

# Returns city at soughtTotal.
# Matrix * Matrix * CitySet * int * double -> int
def findSumWeight(cities: list[list[float]], pher: list[list[float]],
                  used: dict[Int32, Int32], current: Int32, soughtTotal: float) -> Int32:
    runningTotal = 0.0
    next = 0
    for city in range(len(cities)):
        if runningTotal >= soughtTotal:
            break
        if city not in used:
            runningTotal = (runningTotal +
                            cities[current][city] * (1.0 + pher[current][city]))
            next = city
    return next

# Matrix * Matrix -> Path
def genPath(cities: list[list[float]], pher: list[list[float]]) -> Own[list[Int32]]:
    current = random.randint(0, len(cities)-1)
    path = [current]
    used = {current:1}
    while len(used) < len(cities):
        sumWeight = doSumWeight(cities, pher, used, current)
        rndValue = random.random() * sumWeight
        current = findSumWeight(cities, pher, used, current, rndValue)
        path.append(current)
        used[current] = 1
    return path

# Matrix * int * int * int ->Path
def bestPath(cities: list[list[float]], seed: Int32, maxIter: Int32,
             boost: Int32) -> Own[list[Int32]]:
    pher = randomMatrix(len(cities), 0, 0)
    random.seed(seed)
    bestLen = 0.0
    bestPath: list[Int32] = []
    for iter in range(maxIter):
        path = genPath(cities, pher)
        pathLen = pathLength(cities, path)
        if pathLen > bestLen:
            # Remember we are trying to maximize score.
            updatePher(pher, path, boost)
            bestLen = pathLen
            # copy(): the loop rebinds `path` next iteration, so the best-so-far
            # needs its own storage. CPython aliases here, with the same effect.
            bestPath = copy(path)
        evaporatePher(pher, maxIter, boost)
    return bestPath

def main() -> None:
    boost = 5
    iter = 3000
    numCities = 20
    maxDistance = 10
    cityDistanceSeed = 1
    print("starting")
    for n in range(200):
        if n == 100:
            t0 = time.time()  # pypy has stabilized
        seed = n
        cities = randomMatrix(numCities, maxDistance, cityDistanceSeed)
        path = bestPath(cities, seed, iter, boost)
        print(path)
        print("len = ", pathLength(cities, path))
    print(f'TIME {time.time()-t0:.2f}')

if __name__ == "__main__":
    main()
