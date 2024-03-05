# This script runs GRASP metaheuristics for the parking case.
# The script is not optimized for performance and speed, but
# it is easier to explain a demonstrate the concept.

import pandas as pd
import copy
import random
from matplotlib import pyplot as plt

# car lengths
df_cars = pd.DataFrame(
    data=[[1,4],[2,4.5],[3,5],[4,4.1],[5,2.4],[6,5.2],[7,3.7],
        [8,3.5],[9,3.2],[10,4.5],[11,2.3],[12,3.3],[13,3.8],[14,4.6],[15,3]],
        columns=['car','length'])


def plotSolution(df_bestSol):
    df_sideA = copy.copy(df_bestSol[df_bestSol['side']=='A'])
    df_sideA['offset'] = df_sideA['length'].shift(1).fillna(0).cumsum()
    df_sideA.reset_index(drop=True, inplace=True)

    df_sideB = copy.copy(df_bestSol[df_bestSol['side']=='B'])
    df_sideB['offset'] = df_sideB['length'].shift(1).fillna(0).cumsum()
    df_sideB.reset_index(drop=True, inplace=True)

    fig, ax = plt.subplots(figsize=(8, 4))
    for idx, row in df_sideA.iterrows():
        ax.barh(0, row['length'], left=row['offset'], align='edge')

    for idx, row in df_sideB.iterrows():
        ax.barh(1, row['length'], left=row['offset'], align='edge')
    
    ax.set_title('parking sequence')
    ax.axis('off')
    return


def calculateCost(df):
    # calculate and return total lenght, side A lenght and side B length
    lenA = df[df['side']=='A']['length'].sum()
    lenB = df[df['side']=='B']['length'].sum()
    
    return max([lenA,lenB]), lenA, lenB


def initSolution(df, alpha, sideMax=None):
    # create a greed initial solution starting from random car
    df_sol = copy.copy(df)
    df_sol['side'] = None
    randIndex = random.randint(0, len(df)-1)
    df_sol.at[randIndex,'side'] = 'A'
    while 1:
        # define car sides until there are no more candidates
        df_canditates = copy.copy(df_sol[df_sol['side'].isnull()])
        if len(df_canditates) == 0:
            return df_sol
        
        if sideMax is None:
            # in case sideMax is None, try to greedly equilize both sides
            lenMax, lenA, lenB = calculateCost(df_sol)
            df_canditates['dif'] = abs(df_canditates['length'] - (lenA - lenB))
            # add random variance to the greed part
            n = random.choices(
                list(range(0,len(df_canditates))),
                weights=[pow(alpha,n) for n in range(0,len(df_canditates))]
                )[0]
            newIndex = df_canditates.sort_values(by='dif').iloc[n].name
            if lenA > lenB:
                df_sol.at[newIndex,'side'] = 'B'
            else:
                df_sol.at[newIndex,'side'] = 'A'
        else:
            # in case sideMax is None, try to greedly fill the constraint
            lenMax, lenA, lenB = calculateCost(df_sol)
            df_canditates['dif'] = sideMax - lenA - df_canditates['length']
            df_canditates = df_canditates[df_canditates['dif'] > 0]
            if len(df_canditates):
                # add random variance to the greed part
                n = random.choices(
                    list(range(0,len(df_canditates))),
                    weights=[pow(alpha,n) for n in range(0,len(df_canditates))]
                )[0]
                newIndex = df_canditates.sort_values(by='dif').iloc[n].name
                df_sol.at[newIndex,'side'] = 'A'
            else:
                df_sol['side'] = df_sol['side'].fillna('B')
    return None


def localSearch(df, sideMax=None):
    # improve local solution by selecting a random car
    # and trying to swap sides with the first improving option
    bestVal,_,_ = calculateCost(df)
    # add random variance to the local search
    candidate_1 = df.iloc[random.randrange(1,len(df)-1)]
    side_1 = candidate_1.side
    if side_1 == 'A':
        side_2 = 'B'
    else:
        side_2 = 'A'
    df_test = copy.copy(df)
    df_test.at[candidate_1.name,'side'] = side_2

    df_pos = df[df['side'] != side_2]
    df_pos = df_pos.sample(frac=1)
    for idx, candidate_2 in df_pos.iterrows():
        df_test.at[candidate_2.name, 'side'] = side_1
        curVal,lenA,_ = calculateCost(df_test)
        if sideMax is not None:
            # if constraint is violated skip
            if lenA > sideMax:
                df_test.at[candidate_2.name, 'side'] = side_2
                continue

        if curVal < bestVal:
            return df_test
        df_test.at[candidate_2.name, 'side'] = side_2

    return df


def loopGRASP(df, loops, maxIter, alpha, sideMax=None,):
    df_bestSol = None
    bestVal = df['length'].sum()
    for l in range(loops):
        df_curSol = initSolution(df, alpha, sideMax)
        i = 0
        while i < maxIter:
            df_curSol = localSearch(df_curSol,sideMax)
            curVal,_,_ = calculateCost(df_curSol)
            if curVal < bestVal:
                df_bestSol = df_curSol
                bestVal = curVal
                print(bestVal)
                i = 0
            i += 1

    # print(df_bestSol)
        print(calculateCost(df_bestSol))

    plotSolution(df_bestSol)
    return df_bestSol


if __name__ == '__main__':
    result = loopGRASP(df_cars, 25, 100, 0.75, None)
    limSideResult = loopGRASP(df_cars, 25, 100, 0.75, 15)

    val = calculateCost(result)
    print('best car splits: total = {:.2f}, side A = {:.2f}, side B = {:.2f}'.format(val[0],val[1],val[2]))

    val = calculateCost(limSideResult)
    print('best car splits with 15 constraint: total = {:.2f}, side A = {:.2f}, side B = {:.2f}'.format(val[0],val[1],val[2]))
    
    plt.show()
    pass