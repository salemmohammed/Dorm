from pulp import *
import random
import time

def dorm_allocate(resouce_capacity_g, jobs_g, job_demand_g, job_max_worker_g, job_min_worker_g, job_weight_g, fair_assignment_g, pre_assignment_g, theta1, theta2):
    server_num   = len(resouce_capacity_g);
    job_num      = len(jobs_g);
    resource_num = 3;
    servers      = range(server_num);
    jobs         = jobs_g;
    resources    = range(resource_num);
    resources_total  = {};
    job_demand       = job_demand_g; #[job][resource]
    resouce_capacity = resouce_capacity_g; #[server][resource]
    job_max_worker   = job_max_worker_g;
    job_min_worker   = job_min_worker_g;
    job_weight       = job_weight_g;
    pre_assignment     = pre_assignment_g;
    fair_assignment  = fair_assignment_g;

    for i in resources:
        resources_total[i] = sum(resouce_capacity[m][i] for m in servers);

    start_time = time.time();

    prob = LpProblem('cacluate_Dorm', LpMaximize)
    #define main variables
    assignment = LpVariable.dicts(name="assignment", indexs=(jobs, servers), lowBound=0, cat=LpInteger);
    l = LpVariable.dicts(name="l", indexs=jobs, lowBound=0);
    r = LpVariable.dicts(name="r", indexs=jobs, lowBound=0, upBound=1, cat=LpInteger);

    #objective function
    job_worker_num = {};
    for i in jobs:
        job_worker_num[i] = lpSum([assignment[i][j] for j in servers]);

    job_resource_util = {};
    for i in jobs:
        job_resource_util[i] = [];
        for j in resources:
            job_resource_util[i].append(job_worker_num[i]*job_demand[i][j]*1.0/resources_total[j]);

    cluster_resource_util = lpSum([job_resource_util[i][j] for i in jobs for j in resources]);

    prob +=  cluster_resource_util - 0.1*lpSum([r[i] for i in jobs])/job_num;

    #Constraint: Resource Capacity
    for i in servers:
        for j in resources:
            prob += lpSum([job_demand[m][j]*assignment[m][i] for m in jobs]) <= resouce_capacity[i][j];

    #Constrain: max worker number
    for i in jobs:
        prob += lpSum([assignment[i][n] for n in servers]) <= job_max_worker[i];

    #Constrain: min worker number
    for i in jobs:
        prob += lpSum([assignment[i][n] for n in servers]) >= job_min_worker[i];

    #Constraint: define l
    for i in jobs:
        prob += l[i] >= lpSum([assignment[i][j] for j in servers]) \
        * max([1.0*job_demand[i][n]/resources_total[n] for n in resources]) \
        - sum([fair_assignment[i][j] for j in servers]) \
        * max([1.0*job_demand[i][n]/resources_total[n] for n in resources]);

    for i in jobs:
        prob += l[i] >= -lpSum([assignment[i][j] for j in servers]) \
        * max([1.0*job_demand[i][n]/resources_total[n] for n in resources]) \
        + sum([fair_assignment[i][j] for j in servers]) \
        * max([1.0*job_demand[i][n]/resources_total[n] for n in resources]);

    #Constraint: define r
    for i in jobs:
        for j in servers:
            prob += 1000000*r[i] >= assignment[i][j] - pre_assignment[i][j];
            prob += 1000000*r[i] >= -assignment[i][j] + pre_assignment[i][j];

    #Constraint: l
    job_fair_dominant_share = {};
    for i in jobs:
        job_fair_dominant_share[i] = sum([fair_assignment[i][j] for j in servers]) \
            * max([1.0*job_demand[i][n]/resources_total[n] for n in resources]);
    prob += lpSum([l[i] for i in jobs])/(resource_num*sum([job_fair_dominant_share[i] for i in jobs])) <= theta1;

    #Constraint: r
    prob += lpSum([r[i] for i in jobs])*1.0/job_num <= theta2;


    solver = solvers.CPLEX_PY();
    solver.epgap = 0.1;
    # prob.solve(CPLEX());
    solver.solve(prob);
    # prob.solve(GLPK(options=['--mipgap', '0.02']));

    assignment_re = {};
    for i in jobs:
        assignment_re[i]=[];
        for j in servers:
            assignment_re[i].append(int(value(assignment[i][j])));
    print("--- %s seconds ---" % (time.time() - start_time));
    print sum([value(l[i]) for i in jobs])/(resource_num*sum([job_fair_dominant_share[i] for i in jobs]));

    # job_resource_util_val = {};
    # for i in jobs:
    #     job_resource_util_val[i] = [];
    #     for j in resources:
    #         job_resource_util_val[i].append(job_worker_num[i]*job_demand[i][j]*1.0/resources_total[j]);
    # cluster_resource_util_val = lpSum([job_resource_util_val[i][j] for i in jobs for j in resources])
    # print value(cluster_resource_util_val);

    # for i in jobs:
    #     print sum([assignment_re[i][j] for j in servers]),
    # print ' ';
    # for i in jobs:
    #     print sum([fair_assignment[i][j] for j in servers]),

    return assignment_re;

def fair_allocate(method, resouce_capacity_g, jobs_g, job_demand_g, job_max_worker_g, job_min_worker_g, job_weight_g):

    server_num   = len(resouce_capacity_g);
    job_num      = len(jobs_g);
    resource_num = 3;
    servers      = range(server_num);
    jobs         = jobs_g;
    resources    = range(resource_num);
    known_job_sw     = {};
    unknown_job_sw   = {};
    history_job_info = [];
    resources_total  = {};
    job_demand       = job_demand_g; #[job][resource]
    resouce_capacity = resouce_capacity_g; #[server][resource]
    job_max_worker   = job_max_worker_g;
    job_min_worker   = job_min_worker_g;
    job_weight       = job_weight_g;
    iteration_num    = 0;

    for i in resources:
        resources_total[i] = sum(resouce_capacity[m][i] for m in servers);
    #############################
    if method == 'huristic':
        assignment = {};  #[job][server]
        for i in jobs:
            assignment[i]=[];
            for j in servers:
                assignment[i].append(0);

        utilization = []; #[server][resource]
        for i in servers:
            utilization.append([]);
            for j in resources:
                utilization[i].append(0);

        job_sw = {}; #[job]
        for i in jobs:
            job_sw[i] = 0;

        is_full = False;
        while is_full == False and len(job_sw) > 0:
            tmp_sw_value = job_sw.values();
            min_sw_value = min(tmp_sw_value);
            min_sw_index = job_sw.values().index(min_sw_value);
            min_sw_key   = job_sw.keys()[min_sw_index];
            dominant_resource_share = max([1.0*job_demand[min_sw_key][n]/resources_total[n] for n in resources]);
            dominant_resource       = [1.0*job_demand[min_sw_key][n]/resources_total[n] for n in resources].index(dominant_resource_share);
            dominant_resource_util = [utilization[m][dominant_resource]*1.0/resouce_capacity[m][dominant_resource] for m in servers];
            sorted_resource_util = sorted(dominant_resource_util);
            sorted_server = [];
            for i in sorted_resource_util:
                sorted_server.append(dominant_resource_util.index(i));

            for target_server in sorted_server:
                chosen = True;
                for try_resource in resources:
                    if utilization[target_server][try_resource]+job_demand[min_sw_key][try_resource]\
                        > resouce_capacity[target_server][try_resource]:
                        chosen = False;
                        break;
                if chosen == True:
                    assignment[min_sw_key][target_server] = assignment[min_sw_key][target_server] + 1;
                    for try_resource in resources:
                        utilization[target_server][try_resource] = utilization[target_server][try_resource]+job_demand[min_sw_key][try_resource];
                    job_sw[min_sw_key] = sum(assignment[min_sw_key]) \
                        * max([1.0*job_demand[min_sw_key][n]/resources_total[n] for n in resources]) \
                       / job_weight[min_sw_key];
                    if sum(assignment[min_sw_key]) == job_max_worker[min_sw_key]:
                        del job_sw[min_sw_key];
                    break;
            if chosen == False:
                is_full = True;
        return assignment;

    elif method == 'mip':
        start_time = time.time();
        assignment_re = {};
        for i in jobs:
            unknown_job_sw[i] = 0;
        while len(unknown_job_sw) > 0:
            iteration_num = iteration_num + 1;
            print '######->', iteration_num;
            prob = LpProblem('cacluate_fair', LpMaximize)
            #define main variables
            assignment = LpVariable.dicts(name="assignment", indexs=(jobs, servers), lowBound=0, cat=LpInteger);

            #Constraint: Resource Capacity
            for i in servers:
                for j in resources:
                    prob += lpSum([job_demand[m][j]*assignment[m][i] for m in jobs]) <= resouce_capacity[i][j];

            #Constrain: max worker number
            for i in jobs:
                prob += lpSum([assignment[i][n] for n in servers]) <= job_max_worker[i];

            #Constrain: min worker number
            for i in jobs:
                prob += lpSum([assignment[i][n] for n in servers]) >= job_min_worker[i];

            for i in known_job_sw.keys():
                prob += (lpSum([assignment[i][n] for n in servers]) \
                        * max([1.0*job_demand[i][n]/resources_total[n] for n in resources]) \
                        / job_weight[i] - known_job_sw[i]) / known_job_sw[i] \
                        <= 0.05;
                prob += (-lpSum([assignment[i][n] for n in servers]) \
                        * max([1.0*job_demand[i][n]/resources_total[n] for n in resources]) \
                        / job_weight[i] + known_job_sw[i]) / known_job_sw[i] \
                        <= 0.05;

            tau = LpVariable(name='tau', cat='Continuous');

            for i in unknown_job_sw.keys():
                prob += lpSum([assignment[i][n] for n in servers]) \
                        * max([1.0*job_demand[i][n]/resources_total[n] for n in resources]) \
                        / job_weight[i] >= tau;

            for i in known_job_sw.keys():
                prob += lpSum([assignment[i][n] for n in servers]) \
                         * max([1.0*job_demand[i][n]/resources_total[n] for n in resources]) \
                         / job_weight[i] <= tau/0.95;

            prob += tau;
            solver = solvers.CPLEX_PY();
            solver.epgap = 0.05;
            # prob.solve(CPLEX());
            solver.solve(prob);
            # prob.solve(GLPK(options=['--mipgap', '0.02']));

            result = [];
            for i in unknown_job_sw.keys():
                result.append(sum([value(assignment[i][n]) for n in servers]) \
                * max([1.0*job_demand[i][n]/resources_total[n] for n in resources]) \
                / job_weight[i]);
            min_result = min(result);
            min_result_index = unknown_job_sw.keys()[result.index(min_result)];
            known_job_sw[min_result_index] = min_result;
            del unknown_job_sw[min_result_index];

            job_info = {}
            for i in jobs:
                tmp = int(sum([value(assignment[i][n]) for n in servers]));
                job_info[i] = tmp;
                assignment_re[i]=[];
                for j in servers:
                    assignment_re[i].append(int(value(assignment[i][j])));
            history_job_info.append(job_info);

            break_tag = True;
            for i in unknown_job_sw.keys():
                if job_info[i] == job_max_worker[i]:
                    break_tag = False;
                    break;
            if job_info[min_result_index] == job_max_worker[min_result_index]:
                break_tag = False;

            if break_tag == True:
                break;
        print("--- %s seconds ---" % (time.time() - start_time));
        return assignment_re;

def cluster_utilization(resource_num, resources_total, jobs, job_demand, assignment):
    job_worker_num = {};
    for i in jobs:
         job_worker_num[i] = sum(assignment[i]);
    utilization = [];
    for j in range(resource_num):
        utilization.append(sum([1.0*job_worker_num[i]*job_demand[i][j]/resources_total[j] for i in jobs]));
    return utilization;

random.seed(1);
job_num      = 50;
jobs         = range(job_num);
job_demand       = {}; #[job][resource]
job_max_worker   = {};
job_min_worker   = {};
job_weight       = {};
resources_total  = {};

server_num   = 200;
resource_num = 3;
resources    = range(resource_num);
servers      = range(server_num);
resouce_capacity = {}; #[server][resource]

#define resource capacity
for i in servers:
    resouce_capacity[i] = {};
    for j in resources:
        if j==0:
            resouce_capacity[i][j] = 24;
        elif j==1:
            resouce_capacity[i][j] = 200;
        elif j==2:
            resouce_capacity[i][j] = 4;

#define job resource demand, max/min worker number and weight
for i in jobs:
    job_max_worker[i] = random.randint(10,50);
    job_min_worker[i] = random.randint(1,1);
    job_weight[i]     = random.randint(1,10);
    job_demand[i] = {};
    for j in resources:
        if j==0:
            job_demand[i][j] = random.randint(2,8);  #CPU
        elif j==1:
            job_demand[i][j] = random.randint(8,16); #RAM
        elif j==2:
            job_demand[i][j] = random.randint(1,1);  #GPU

for i in resources:
    resources_total[i] = sum(resouce_capacity[m][i] for m in servers);

fair_assignment = fair_allocate('huristic', resouce_capacity, jobs, job_demand, job_max_worker, job_min_worker, job_weight);

pre_assignment = {};
for i in jobs:
    pre_assignment[i] = [];
    for j in servers:
        pre_assignment[i].append(0);

dorm_assignment = dorm_allocate(resouce_capacity, jobs, job_demand, job_max_worker, job_min_worker, job_weight, fair_assignment, pre_assignment, 0.01, 1);

########
#a new job#
########
job_num      = 51;
jobs         = range(job_num);
job_demand[50] = {};
job_demand[50][0] = 4;
job_demand[50][1] = 10;
job_demand[50][2] = 1;
job_max_worker[50]= 30;
job_min_worker[50]= 1;
job_weight[50]    = 5;

fair_assignment = fair_allocate('huristic', resouce_capacity, jobs, job_demand, job_max_worker, job_min_worker, job_weight);
pre_assignment  = dorm_assignment;
pre_assignment[50] = [int(0)]*server_num;
dorm_assignment = dorm_allocate(resouce_capacity, jobs, job_demand, job_max_worker, job_min_worker, job_weight, fair_assignment, pre_assignment, 0.1, 0.2);

for i in jobs:
    print sum(pre_assignment[i]),
print '';
for i in jobs:
    print sum(dorm_assignment[i]),
print '';
print sum(cluster_utilization(resource_num, resources_total, jobs, job_demand, dorm_assignment));
print sum(cluster_utilization(resource_num, resources_total, jobs, job_demand, fair_assignment));

adjust_job_num=0;
for i in jobs:
    for j in servers:
        if abs(dorm_assignment[i][j] - pre_assignment[i][j]) > 0:
            adjust_job_num = adjust_job_num + 1;
            break;
print adjust_job_num;
