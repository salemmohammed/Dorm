from pulp import *

prob = LpProblem('lptest', LpMaximize)

#lamda = 0.05
lamda = 0.0
relaxed_fairness = 0.2
num_app = 3
#'''
cpu_app = [1, 4, 1]
ram_app = [4, 2, 2]
weight  = [1, 1, 1]
domain  = ['cpu', 'cpu', 'cpu']
'''

#cpu_app = [1, 3]
#ram_app = [3, 4]
num_app = 2
cpu_app = [1, 4]
ram_app = [4, 2]
weight  = [1, 1]
domain  = ['cpu', 'cpu', 'cpu']
'''
num_server = 2
#cpu_server = [9, 9]
#ram_server = [18, 18]
cpu_server = [12, 24]
ram_server = [128, 128]

old_alloc = [[12,12], [0,3], [0,0]] #[j][i], j-th app, i-th server

existing_app = []
for i in range(num_app):
    if sum(old_alloc[i]) > 0:
        existing_app.append(i)

global_cpu_num = sum(cpu_server)
global_ram_num = sum(ram_server)
global_cpu_ram_ratio = global_cpu_num * 1.0 / global_ram_num

app_cpu_ram_ratio = []
for i in range(num_app):
    app_cpu_ram_ratio.append(cpu_app[i] * 1.0 / ram_app[i])

'''
for i in range(num_app):
    if app_cpu_ram_ratio[i] >= global_cpu_ram_ratio:
        domain[i] = 'cpu'
    else:
        domain[i] = 'ram'
'''

#domain  = ['ram', 'cpu']

print "application domain:"
for i in range(num_app):
    print domain[i], '\t',
print ""
print "global cpu ram ratio: ", global_cpu_ram_ratio
print ""

variables = []
single_variables = []
regu = []
single_regu = []

weight_sum = sum(weight)
for i in range(num_app):
    weight[i] = weight[i]*1.0/weight_sum

for i in range(num_server):
    variables.append([])
    regu.append([])
    for j in range(num_app):
        t = LpVariable('app-'+str(i)+'-'+str(j), lowBound=0, cat=LpInteger)
        variables[i].append(t)
        single_variables.append(t)
        tmp_regu = LpVariable('regu-'+str(i)+'-'+str(j))
        regu[i].append(tmp_regu)
        if i in existing_app:
            single_regu.append(tmp_regu)

for i in range(num_server):
    for j in range(num_app):
        #   prob += max(-variables[i][j] + old_alloc[j][i], 0)
        prob += regu[i][j] >= -variables[i][j] + old_alloc[j][i]
        prob += regu[i][j] >= 0

#CPU
for i in range(num_server):
    prob += sum([cpu_app[j]*variables[i][j]  for j in range(num_app)]) <= cpu_server[i]

for i in range(num_server):
    prob += sum([ram_app[j]*variables[i][j]  for j in range(num_app)]) <= ram_server[i]


cpu_total = sum(cpu_server)
ram_total = sum(ram_server)

cpu_app_used = []
for i in range(num_server):
    for j in range(num_app):
        if j < len(cpu_app_used):
            cpu_app_used[j].append(cpu_app[j]*variables[i][j])
        else:
            cpu_app_used.append([cpu_app[j]*variables[i][j]])

ram_app_used = []
for i in range(num_server):
    for j in range(num_app):
        if j < len(ram_app_used):
            ram_app_used[j].append(ram_app[j]*variables[i][j])
        else:
            ram_app_used.append([ram_app[j]*variables[i][j]])

domain_share = []
cpu_app_share = {}
ram_app_share = {}

cpu_app_share2 = []
ram_app_share2 = []
for i in range(num_app):
    cpu_app_share[i] = LpVariable('cpu_app_share_'+str(i), lowBound = 0)
    ram_app_share[i] = LpVariable('ram_app_share_'+str(i), lowBound = 0)
    prob += cpu_app_share[i] ==  sum(cpu_app_used[i]) *1.0 / cpu_total
    prob += ram_app_share[i] ==  sum(ram_app_used[i]) *1.0/ ram_total
    cpu_app_share2.append(cpu_app_share[i])
    ram_app_share2.append(ram_app_share[i])

    if domain[i] == 'cpu':
        domain_share.append(cpu_app_share[i])
    else:
        domain_share.append(ram_app_share[i])

prob += sum(cpu_app_share2) + sum(ram_app_share2)  - lamda * sum([j for j in single_regu])

for i in range(num_app):
   # prob  += domain_share[i] - sum(domain_share) * weight[i] == 0
    prob  += domain_share[i] - sum(domain_share) * weight[i] >= -relaxed_fairness
    prob  += domain_share[i] - sum(domain_share) * weight[i] <=  relaxed_fairness

#x1 = LpVariable('x1', lowBound = 0, cat=LpInteger)
#x2 = LpVariable('x2', lowBound = 0, cat=LpInteger)
#prob += x1 + x2
#prob += 4*x1 + x2 <= 130
#prob += x1 + 3*x2 <= 89
#prob += 6*variables[0][0] - 9*variables[0][1] == 0

#prob.solve(GLPK(options=['--mipgap', '0.01']))
#prob.solve(CPLEX(options=['--mipgap', '0.01']))
#prob.solve(GLPK())
prob.solve(CPLEX())
#for v in prob.variables():
#    print v.name, '=', v.varValue

result = prob.variablesDict();

total_app_num = [];

print "\napp allocations:"
for i in range(num_server):
    print "Server ", i, ' ->\t',
    for j in range(num_app):
        print result['app_'+str(i)+'_'+str(j)].varValue, '\t',
        if j >= len(total_app_num):
            total_app_num.append(result['app_'+str(i)+'_'+str(j)].varValue)
        else:
            total_app_num[j] += result['app_'+str(i)+'_'+str(j)].varValue
    print ''

for i in range(num_app):
    print 'app ', i, ' num -> ', total_app_num[i]

print "\nregu:"
for i in range(num_server):
    print "Server ", i, ' ->\t',
    for j in range(num_app):
        print result['regu_'+str(i)+'_'+str(j)].varValue, '\t',
    print ''

print "\nCPU utilization: ",
total_cpu = 0
for i in range(num_app):
    total_cpu += cpu_app[i] * total_app_num[i]
print total_cpu * 1.0 / sum(cpu_server)

print "\nRAM utilization: ",
total_ram = 0
for i in range(num_app):
    total_ram += ram_app[i] * total_app_num[i]
print total_ram * 1.0 / sum(ram_server)
