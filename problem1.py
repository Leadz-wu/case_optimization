import pandas as pd
import pyomo.environ as pyo
from matplotlib import pyplot as plt

class Job():
    # job class properties
    def __init__(self, row):
        self.job = row['job']
        self.process_time = row['process_time']
        self.setup_time = row['setup_time']
        self.release_time = row['release_time']
        self.deadline = row['deadline']


def buildVars(model, dict_job):
    # function to create model sets and variables
    list_job = list(dict_job.keys())

    # define sets
    model.setJobs = pyo.Set(initialize=list_job + [''])
    model.setVars = pyo.Set(initialize=[
        [j1, j2] for j1 in  list_job+[''] for j2 in list_job
        if j1 != j2])
    
    # define variables
    model.varSeq = pyo.Var(model.setVars, domain=pyo.Binary)
    model.varTime = pyo.Var(model.setVars, domain=pyo.NonNegativeReals)
    model.varDelay = pyo.Var(model.setJobs, domain=pyo.NonNegativeReals)
    # model.varSlack = pyo.Var(model.setJobs, domain=pyo.NonNegativeReals)
    model.varMakeSpan = pyo.Var(domain=pyo.NonNegativeReals)
    return


def buildConstraints(model, dict_job):
    # function to create model constraints
    list_job = list(dict_job.keys())

    # single start can be set for each job
    def constrSingle(model, job):
        if job == '':
            return pyo.Constraint.Feasible
        else:
            return sum(model.varSeq[j, job] for j in list_job + [''] if j != job) == 1
    model.constrSingle = pyo.Constraint(model.setJobs, rule=constrSingle)

    # single following job
    def constrNext(model, job):
        return sum(model.varSeq[job, j] for j in list_job if j != job) <= 1
    model.constrNext = pyo.Constraint(model.setJobs, rule=constrNext)

    # bigM decision and time
    def constrBigM(model,j1,j2):
        return model.varSeq[j1, j2]*9999 >= model.varTime[j1, j2]
    model.constrBigM = pyo.Constraint(model.setVars, rule=constrBigM)

    # time sequence
    def constrTimeSeq(model,j1,j2):
        return (
            sum(model.varTime[j,j1] if j1 != '' else 0 for j in list_job + [''] if j != j1)
            +
            sum(model.varSeq[j,j1]*dict_job[j1].process_time if j1 != '' else 0 for j in list_job + [''] if j != j1)
            +
            dict_job[j2].setup_time
            -
            model.varTime[j1,j2]
            <=
            (1 - model.varSeq[j1,j2])*9999
        )
    model.constrTimeSeq = pyo.Constraint(model.setVars, rule=constrTimeSeq)

    # time window (release time)
    def constrDelay(model,j1,j2):
        return model.varTime[j1,j2] >= model.varSeq[j1,j2]*dict_job[j2].release_time
    model.constrDelay = pyo.Constraint(model.setVars, rule=constrDelay)

    # time window (deadline)
    def constrDeadline(model,j1,j2):
        return model.varTime[j1,j2] <= model.varDelay[j2] + dict_job[j2].deadline
    model.constrDeadline = pyo.Constraint(model.setVars, rule=constrDeadline)

    # make span
    def constrMakeSpan(model,j1,j2):
        return model.varTime[j1,j2] + dict_job[j2].process_time <= model.varMakeSpan
    model.constrMakeSpan = pyo.Constraint(model.setVars, rule=constrMakeSpan)



def buildObjective(model, dict_job):
    # function to create model objectives
    # two objectives: reduce total deadline delay and unproductive time
    def ObjRule(model):
        return sum([model.varDelay[j]*99 + model.varMakeSpan for j in  dict_job.keys()])
    model.obj1 = pyo.Objective(rule=ObjRule, sense=pyo.minimize)
    return


def solutionToPandas(model):
    # decision variables dataframe
    df_varSeq = pd.DataFrame()
    for v in model.varSeq:
        if model.varSeq[v].value > 0.1:
            df_varSeq = pd.concat([
                df_varSeq,
                    pd.DataFrame(
                    [[v[0],
                    v[1],
                    model.varSeq[v].value]],
                    columns = ['prev_job','cur_job','val']
                )]
            )

    # start time dataframe
    df_varTime = pd.DataFrame()
    for v in model.varTime:
        if (model.varTime[v].value is not None) & (model.varTime[v].value > 0.1):
            df_varTime = pd.concat([
                df_varTime,
                    pd.DataFrame(
                    [[v[0],
                    v[1],
                    model.varTime[v].value]],
                    columns = ['prev_job','cur_job','val']
                )]
            )
    
    # delay time dataframe
    df_varDelay = pd.DataFrame()
    for v in model.varDelay:
        if (model.varDelay[v].value is not None) and (model.varDelay[v].value > 0.1):
            df_varDelay = pd.concat([
                df_varDelay,
                    pd.DataFrame(
                    [[v,
                    model.varDelay[v].value]],
                    columns = ['cur_job','val']
                )]
            )
    writer = pd.ExcelWriter('problem1_output.xlsx', engine='openpyxl')
    df_varSeq.to_excel(writer, sheet_name="varSeq", index=False)
    df_varTime.to_excel(writer, sheet_name="varTime", index=False)
    df_varDelay.to_excel(writer, sheet_name="varDelay", index=False)
    writer.close()

    return df_varTime, df_varDelay

def plotSolution(df_jobs, df_varTime):
    # plot result
    df_varTime = df_varTime.merge(df_jobs, how='left', left_on='cur_job', right_on='job')
    df_varTime['end_time'] = df_varTime['val'] + df_varTime['process_time']
    df_varTime = df_varTime.sort_values(by='end_time', ascending=False)
    df_varTime.reset_index(drop=True, inplace=True)
    
    fig, ax = plt.subplots(figsize=(6, 2))
    for idx, row in df_varTime.iterrows():
        ax.barh(0, row['process_time'], left=row['val'], align='edge')
        ax.barh(0, row['setup_time'], left=row['val']-row['setup_time'],
            align='edge', color='gray', hatch='/', alpha=0.25)
        ax.text(row['val']+row['process_time']/2.5,0.4, row['cur_job'],
            color = 'black', ha = 'left', va = 'center', rotation=90)
        
        
    # for idx, row in :
    #     ax.patches[idx].text(job['cur_job'],0.4, job, color = 'black', ha = 'left', va = 'center', rotation=90)
    ax.set_title('job scheduling')
    ax.axis('off')
    fig.show()
    return

if __name__ == '__main__':
    # read input csv and create jobs objects
    df_jobs = pd.read_csv('jobs.csv',sep=';')
    df_jobs = df_jobs.head(8)
    dict_job = {row['job']:Job(row) for idx, row in df_jobs.iterrows()}

    model = pyo.ConcreteModel()

    buildVars(model, dict_job)
    buildConstraints(model, dict_job)
    buildObjective(model, dict_job)

    opt = pyo.SolverFactory('glpk')
    result = opt.solve(model, tee=True)
    result.write()
    model.solutions.load_from(result)

    # compile output
    df_varTime, df_varDelay = solutionToPandas(model)
    plotSolution(df_jobs, df_varTime)
    print('total make span: ', model.varMakeSpan.value)
    print('total delay: ', df_varDelay['val'].sum())
    pass