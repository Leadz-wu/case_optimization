# This script formulates and solves a container shipping problem
import pandas as pd
import pyomo.environ as pyo
from matplotlib import pyplot as plt

class Containers():
    def __init__(self, df_containers):
        # create dictionaries for easy index access
        self.dict_c = {}
        self.dict_co = {}
        self.dict_cop = {}
        for idx, row in df_containers.iterrows():
            c = row['Container']
            o = row['Sales Order']
            p = row['Steel Pipe']
            weight = row['Steel Pipe weight (kg)']
            volume = row['Steel Pipe volume (m³)']
            if c not in self.dict_c:
                self.dict_c[c] = [[c,o]]
            else:
                self.dict_c[c] = self.dict_c[c] + [[c,o]]
            if (c,o) not in self.dict_co:
                self.dict_co[c,o] = [[c,o,p]]
            else:
                self.dict_co[c,o] = self.dict_co[c,o] + [[c,o,p]]
            self.dict_cop[c,o,p] = [weight, volume]

    
def buildVars(model, containers):
    # define sets
    model.set_c = pyo.Set(initialize=containers.dict_c.keys())
    model.set_co = pyo.Set(initialize=containers.dict_co.keys())
    model.set_cop = pyo.Set(initialize=containers.dict_cop.keys())
    
    # define variables
    model.varPipes = pyo.Var(model.set_cop, domain=pyo.Binary)
    model.varContainers = pyo.Var(model.set_c, domain=pyo.Binary)
    return


def buildConstraints(model, containers):
    # function to create model constraints

    # containers to product relationship
    def constrContainer(model, c):
        return sum(
            model.varPipes[c,o,p] for c1,o in containers.dict_c[c] for c2,o,p in containers.dict_co[c,o]
            ) <= model.varContainers[c] * 100
    model.constrContainer = pyo.Constraint(model.set_c, rule=constrContainer)

    def constrContainer2(model, c):
        return sum(
            model.varPipes[c,o,p] for c1,o in containers.dict_c[c] for c2,o,p in containers.dict_co[c,o]
            ) >= model.varContainers[c]
    model.constrContainer2 = pyo.Constraint(model.set_c, rule=constrContainer2)

    # container order limit
    def constrOrder(model, c, o):
        return sum(
            model.varPipes[c,o,p] for c1,o,p in containers.dict_co[c,o]
            ) <= 1
    model.constrOrder = pyo.Constraint(model.set_co, rule=constrOrder)

    # max containers
    def constrMaxContainer(model):
        return sum(
            model.varContainers[c] for c in model.set_c
            ) == 35
    model.constrMaxContainer = pyo.Constraint(rule=constrMaxContainer)

    # weight constraint
    def constrWeight(model):
        return sum(
            model.varPipes[c,o,p]*containers.dict_cop[c,o,p][0] for c,o,p in model.set_cop
            ) == 18844
    model.constrWeight = pyo.Constraint(rule=constrWeight)

    # volume constraint
    def constrVolume(model):
        return sum(
            model.varPipes[c,o,p]*containers.dict_cop[c,o,p][1] for c,o,p in model.set_cop
            ) == 5163.69
    model.constrVolume = pyo.Constraint(rule=constrVolume)

    return


def removeSolution(model,containers):
    # add a new constraint to remove the original possibility
    totalPipes = 0
    for c,o,p in model.set_cop:
        if model.varPipes[c,o,p].value is not None and model.varPipes[c,o,p].value > 0.5:
            totalPipes += model.varPipes[c,o,p].value

    def constrOriginal(model):
        return sum(
            model.varPipes[c,o,p] for c,o,p in model.set_cop
            if model.varPipes[c,o,p].value > 0.5
            ) <= totalPipes - 0.5
    model.constrOriginal = pyo.Constraint(rule=constrOriginal)

    return

def solutionToPandas(model,containers,file):
    # create result dataframes and save in xlsx file
    # decision variables dataframe
    df_varPipes = pd.DataFrame()

    for v in model.varPipes:
        if model.varPipes[v].value > 0.5:
            df_varPipes = pd.concat([df_varPipes,
                pd.DataFrame(
                    [[v[0],v[1],v[2],model.varPipes[v].value,
                        containers.dict_cop[v[0],v[1],v[2]][0],
                        containers.dict_cop[v[0],v[1],v[2]][1]]],
                    columns = ['Container','Sales Order','Steel Pipe','val','weight','volume'])
            ])

    df_varPipes.to_excel(file, index=False)

    return df_varPipes

if __name__ == '__main__':
    # read input csv and create jobs objects
    df_containers = pd.read_excel('data.xlsx')
    containers = Containers(df_containers)

    model = pyo.ConcreteModel()
    opt = pyo.SolverFactory('glpk')

    buildVars(model, containers)
    buildConstraints(model, containers)

    # solve initial problem
    result = opt.solve(model, tee=True)
    model.solutions.load_from(result)
    solutionToPandas(model,containers,'problem2_output_a.xlsx')

    # check if there is another solution
    removeSolution(model,containers)
    
    result = opt.solve(model, tee=True)
    model.solutions.load_from(result)
    solutionToPandas(model,containers,'problem2_output_b.xlsx')

    model.display()

    pass