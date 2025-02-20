import random
'''
split the three functions calculate_rates, s_history, and check_collision_and_idle out,
since they are shared by all the protocols.
'''
def calculate_rates(hosts, setting, total_idle_time):
    total_success_num = 0
    for h in hosts:
        total_success_num += h["success_num"]
    total_success_time = total_success_num * setting.packet_time
    total_collision_time = setting.total_time - total_success_time - total_idle_time
    return total_success_time / setting.total_time, total_idle_time / setting.total_time, total_collision_time / setting.total_time

def s_history(hosts, setting):
    packets_times = setting.gen_packets()
    for h in hosts:
        s = ""
        for t in range(setting.total_time):
            if len(packets_times[h["id"]]) > 0 and packets_times[h["id"]][0] == t:
                s += "V"
                packets_times[h["id"]].pop(0)
            else:
                s += " "
        print(f"    {s}")
        print(f"h{h['id']}: {h['history']}")    

def check_collision_and_idle(hosts, history, total_idle_time):
    sending_list = []
    is_idle_time = True
    for h in hosts:
        if h["status"] == 1:
            sending_list.append(h)
            is_idle_time = False
        if history[h["id"]] != ".":
            is_idle_time = False
                
    if len(sending_list) > 1:
        for h in sending_list:
            h["collision"] = True
    if is_idle_time:
        total_idle_time += 1
    return total_idle_time


def aloha(setting, show_history=False):
    
    # delete "action_to_do" since it is duplicated with "status"
    hosts = [
        {
            "id": i,
            "status": 0,         
            "packet_num": 0,   
            "remain_length": 0,  
            "wait_time": 0,      
            "collision": False,
            "success_num": 0,
            "collision_num": 0,
            "history": "",     
        }
        for i in range(setting.host_num)
    ]
    
    packets_times = setting.gen_packets() 
    total_idle_time = 0
    for t in range(setting.total_time):
        history = ["." for i in range(setting.host_num)]
        
        for h in hosts:
            if len(packets_times[h["id"]]) > 0 and packets_times[h["id"]][0] == t:
                packets_times[h["id"]].pop(0)
                h["packet_num"] += 1

        # leave only aloha logic
        for h in hosts:
            
            if h["status"] == 0:
                if h["wait_time"] > 0:
                    h["wait_time"] -= 1

                elif h["packet_num"] > 0:
                    h["status"] = 1
                    h["remain_length"] = setting.packet_time

        total_idle_time = check_collision_and_idle(hosts, history, total_idle_time)
            
        for h in hosts:
            if h["status"] == 1:
                if len(h["history"]) == 0 or (h["history"][-1] != "<" and h["history"][-1] != "-"):
                    history[h["id"]] = "<"
                else:
                    history[h["id"]] = "-"
                h["remain_length"] -= 1
                if h["remain_length"] <= 0:
                    if h["collision"]:
                        h["wait_time"] = random.randint(0, setting.max_collision_wait_time)
                        h["status"] = 0
                        h["collision_num"] += 1
                        history[h["id"]] = "|"
                    else:
                        h["status"] = 0
                        h["success_num"] += 1
                        h["packet_num"] -= 1
                        history[h["id"]] = ">"
                    h["collision"] = False
            h["history"] += history[h["id"]]

    if show_history: s_history(hosts, setting)
                
    return calculate_rates(hosts, setting, total_idle_time) 

def slotted_aloha(setting, show_history=False):
    hosts = [
        {
            "id": i,
            "status": 0,         
            "packet_num": 0,   
            "remain_length": 0,  
            "wait_time": 0,      
            "collision": False,
            "success_num": 0,
            "collision_num": 0,
            "history": "",       
        }
        for i in range(setting.host_num)
    ]
    
    packets_times = setting.gen_packets() 
    total_idle_time = 0
    for t in range(setting.total_time):
        history = ["." for i in range(setting.host_num)]
        
        for h in hosts:
            if len(packets_times[h["id"]]) > 0 and packets_times[h["id"]][0] == t:
                packets_times[h["id"]].pop(0)
                h["packet_num"] += 1

        # leave only slotted aloha logic
        for h in hosts:
            
            if h["status"] == 0:
                if h["wait_time"] > 0:
                    h["wait_time"] -= 1

                elif h["packet_num"] > 0 and t % setting.packet_time == 0:
                    h["status"] = 1
                    h["remain_length"] = setting.packet_time
                    
            elif h["status"] == 2 and t % setting.packet_time == 0:
                r = random.random()
                if r < setting.p_resend:
                    h["status"] = 1
                    h["remain_length"] = setting.packet_time

        total_idle_time = check_collision_and_idle(hosts, history, total_idle_time)
            
        for h in hosts:
            if h["status"] == 1:
                if len(h["history"]) == 0 or (h["history"][-1] != "<" and h["history"][-1] != "-"):
                    history[h["id"]] = "<"
                else:
                    history[h["id"]] = "-"
                h["remain_length"] -= 1
                if h["remain_length"] <= 0:
                    if h["collision"]:
                        h["status"] = 2
                        h["collision_num"] += 1
                        history[h["id"]] = "|"
                    else:
                        h["status"] = 0
                        h["success_num"] += 1
                        h["packet_num"] -= 1
                        history[h["id"]] = ">"
                    h["collision"] = False
            h["history"] += history[h["id"]]

    if show_history: s_history(hosts, setting)
    
    return calculate_rates(hosts, setting, total_idle_time)

def csma(setting, one_persistent=False, show_history=False):
    hosts = [
        {
            "id": i,
            "status": 0,        
            "packet_num": 0,   
            "remain_length": 0,  
            "wait_time": 0,      
            "collision": False,
            "success_num": 0,
            "collision_num": 0,
            "history": "",      
        }
        for i in range(setting.host_num)
    ]
    
    packets_times = setting.gen_packets() 
    total_idle_time = 0
    for t in range(setting.total_time):
        history = ["." for i in range(setting.host_num)]
        
        for h in hosts:
            if len(packets_times[h["id"]]) > 0 and packets_times[h["id"]][0] == t:
                packets_times[h["id"]].pop(0)
                h["packet_num"] += 1

        # leave only csma logic
        for h in hosts:
            if h["status"] == 0:
                if h["wait_time"] > 0:
                    h["wait_time"] -= 1

                elif h["packet_num"] > 0:
                    others_sending = False
                    for others in hosts:
                        if others["id"] == h["id"]:
                            continue
                        if (
                            setting.link_delay >= 0
                            and t > (setting.link_delay + 1)
                            and (
                                others["history"][t - (setting.link_delay + 1)] == "-"
                                or others["history"][t - (setting.link_delay + 1)] == "<"
                            )
                        ):
                            others_sending = True
                    
                    if not others_sending:
                        h["status"] = 1
                        h["remain_length"] = setting.packet_time
                    else:
                        if not one_persistent:
                            h["wait_time"] = random.randint(0, setting.max_collision_wait_time)

        total_idle_time = check_collision_and_idle(hosts, history, total_idle_time)
            
        for h in hosts:
            if h["status"] == 1:
                if len(h["history"]) == 0 or (h["history"][-1] != "<" and h["history"][-1] != "-"):
                    history[h["id"]] = "<"
                else:
                    history[h["id"]] = "-"
                h["remain_length"] -= 1
                if h["remain_length"] <= 0:  
                    if h["collision"]:
                        h["wait_time"] = random.randint(0, setting.max_collision_wait_time)
                        h["status"] = 0
                        h["collision_num"] += 1
                        history[h["id"]] = "|"
                    else:
                        h["status"] = 0
                        h["success_num"] += 1
                        h["packet_num"] -= 1
                        history[h["id"]] = ">"
                    h["collision"] = False
            h["history"] += history[h["id"]]
            
    if show_history: s_history(hosts, setting)
    
    return calculate_rates(hosts, setting, total_idle_time)

def csma_cd(setting, one_persistent=False, show_history=False):
    hosts = [
        {
            "id": i,
            "status": 0,         
            "packet_num": 0,   
            "remain_length": 0, 
            "wait_time": 0,   
            "collision": False,
            "success_num": 0,
            "collision_num": 0,
            "history": "",       
        }
        for i in range(setting.host_num)
    ]
    
    packets_times = setting.gen_packets()
    total_idle_time = 0
    for t in range(setting.total_time):
        history = ["." for i in range(setting.host_num)]
        
        for h in hosts:
            if len(packets_times[h["id"]]) > 0 and packets_times[h["id"]][0] == t:
                packets_times[h["id"]].pop(0)
                h["packet_num"] += 1

        # leave only csma/cd logic
        for h in hosts:
            if h["status"] == 0:
                if h["wait_time"] > 0:
                    h["wait_time"] -= 1

                elif h["packet_num"] > 0:
                    others_sending = False
                    for others in hosts:
                        if others["id"] == h["id"]:
                            continue
                        if (
                            setting.link_delay >= 0
                            and t > (setting.link_delay + 1)
                            and (
                                others["history"][t - (setting.link_delay + 1)] == "-"
                                or others["history"][t - (setting.link_delay + 1)] == "<"
                            )
                        ):
                            others_sending = True
                    
                    if not others_sending:
                        h["status"] = 1
                        h["remain_length"] = setting.packet_time
                    else:
                        if not one_persistent:
                            h["wait_time"] = random.randint(0, setting.max_collision_wait_time)
            
            elif h["status"] == 1:
                others_sending = False
                for others in hosts:
                    if others["id"] == h["id"]:
                        continue
                    if (
                        setting.link_delay >= 0
                        and t > (setting.link_delay + 1)
                        and (
                            others["history"][t - (setting.link_delay + 1)] == "-"
                            or others["history"][t - (setting.link_delay + 1)] == "<"
                        )
                    ):
                        others_sending = True
                if others_sending:
                    h["status"] = 3
                
        for h in hosts:
            if h["status"] == 3:
                h["collision"] = False
                h["remain_length"] = 0
                h["collision_num"] += 1
                h["wait_time"] = random.randint(0, setting.max_collision_wait_time)
                history[h["id"]] = "|"
                h["status"] = 0
        
        total_idle_time = check_collision_and_idle(hosts, history, total_idle_time)
        
        for h in hosts:
            if h["status"] == 1:
                if len(h["history"]) == 0 or (h["history"][-1] != "<" and h["history"][-1] != "-"):
                    history[h["id"]] = "<"
                else:
                    history[h["id"]] = "-"
                h["remain_length"] -= 1
                if h["remain_length"] <= 0:
                    if h["collision"]:
                        h["status"] = 2
                        history[h["id"]] = "|"
                    else:
                        h["status"] = 0
                        h["success_num"] += 1
                        h["packet_num"] -= 1
                        history[h["id"]] = ">"
                    h["collision"] = False
            h["history"] += history[h["id"]]
            
    if show_history: s_history(hosts, setting)
    
    return calculate_rates(hosts, setting, total_idle_time)
