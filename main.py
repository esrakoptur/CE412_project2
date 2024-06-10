import simpy
import random
import pandas as pd

# --- GLOBAL PARAMETERS ---
RANDOM_SEED = 42
SIM_TIME = 40 * 8 * 60  # Simulation time: 40 days, 8-hour shifts (in minutes)
RAW_MATERIAL_ARRIVAL_TIME = {
    "ProductA": 15,  # Minutes (example)
    "ProductB": 20,  # Minutes (example)
}
NUM_OPERATORS = {
    "Day": 20,
    "Evening": 15,
    "Night": 10,
}

# --- PRODUCT TYPES & PROCESSING TIMES (example) ---
PRODUCT_TYPES = ["ProductA", "ProductB"]
PROCESSING_TIMES = {
    "ProductA": {
        "Machining": {"min": 10, "max": 20},  # Minutes
        "Assembly": {"min": 20, "max": 30},  # Minutes
        "QualityControl": {"min": 3, "max": 7},  # Minutes
        "Packaging": {"min": 1, "max": 3},  # Minutes
    },
    "ProductB": {
        "Machining": {"min": 15, "max": 25},  # Minutes
        "Assembly": {"min": 25, "max": 35},  # Minutes
        "QualityControl": {"min": 5, "max": 9},  # Minutes
        "Packaging": {"min": 2, "max": 4},  # Minutes
    },
}

# --- MACHINE PARAMETERS (example) ---
NUM_MACHINES = {
    "Machining": 5,
    "Assembly": 8,
    "QualityControl": 3,
    "Packaging": 2,
}
MACHINE_BREAKDOWN_TIME = {
    "Machining": {"min": 4 * 60, "max": 8 * 60},  # Hours to minutes
    "Assembly": {"min": 6 * 60, "max": 10 * 60},
    "QualityControl": {"min": 2 * 60, "max": 4 * 60},
    "Packaging": {"min": 1 * 60, "max": 2 * 60},
}
MACHINE_REPAIR_TIME = {
    "Machining": {"min": 1 * 60, "max": 3 * 60},  # Minutes
    "Assembly": {"min": 2 * 60, "max": 4 * 60},
    "QualityControl": {"min": 30, "max": 60},
    "Packaging": {"min": 15, "max": 30},
}


class Machine:
    def __init__(self, env, machine_type, quantity):
        self.env = env
        self.machine_type = machine_type
        self.machines = simpy.Resource(env, capacity=quantity)
        self.breakdown_time = MACHINE_BREAKDOWN_TIME[machine_type]
        self.repair_time = MACHINE_REPAIR_TIME[machine_type]

    def process_product(self, product_type):
        processing_time = random.randint(
            PROCESSING_TIMES[product_type][self.machine_type]["min"],
            PROCESSING_TIMES[product_type][self.machine_type]["max"],
        )
        yield self.env.timeout(processing_time)

    def generate_breakdown(self):
        while True:
            breakdown_duration = random.randint(
                self.breakdown_time["min"], self.breakdown_time["max"]
            )
            yield self.env.timeout(breakdown_duration)
            with self.machines.request() as request:
                yield request
                print(
                    f"{self.env.now:.2f}: Machine breakdown in {self.machine_type}!"
                )
                repair_duration = random.randint(
                    self.repair_time["min"], self.repair_time["max"]
                )
                yield self.env.timeout(repair_duration)
                print(
                    f"{self.env.now:.2f}: {self.machine_type} machine repaired."
                )


def produce_product(env, product_name, product_type, machines):
    global PRODUCTS_PRODUCED
    start_time = env.now
    print(
        f"{env.now:.2f}: Product {product_name} ({product_type}) entered the production line."
    )
    for machine_type in [
        "Machining",
        "Assembly",
        "QualityControl",
        "Packaging",
    ]:
        with machines[machine_type].machines.request() as request:
            yield request
            waiting_time = env.now - start_time
            print(
                f"{env.now:.2f}: Product {product_name} ({product_type}) at {machine_type}. Waiting Time: {waiting_time:.2f}"
            )
            yield env.process(
                machines[machine_type].process_product(product_type)
            )
            start_time = env.now
    PRODUCTS_PRODUCED += 1
    print(
        f"{env.now:.2f}: Product {product_name} ({product_type}) finished production!"
    )


def send_raw_material(env, product_type, machines):
    global RAW_MATERIALS_USED
    i = 1
    while True:
        yield env.timeout(
            random.expovariate(1.0 / RAW_MATERIAL_ARRIVAL_TIME[product_type])
        )
        RAW_MATERIALS_USED += 1
        env.process(
            produce_product(
                env, f"{product_type}-{i}", product_type, machines
            )
        )
        i += 1


def change_shift(env):
    global NUM_OPERATORS
    current_shift = "Day"
    while True:
        yield env.timeout(8 * 60)  # 8-hour shift
        current_shift = (
            "Evening"
            if current_shift == "Day"
            else "Night"
            if current_shift == "Evening"
            else "Day"
        )
        print(f"{env.now:.2f}: Shift changed to {current_shift}.")


def run_scenario(
    env,
    num_machines,
    shift_schedules,
    simulation_time=SIM_TIME,
):
    global PRODUCTS_PRODUCED, RAW_MATERIALS_USED
    PRODUCTS_PRODUCED = 0
    RAW_MATERIALS_USED = 0
    machines = {
        machine_type: Machine(env, machine_type, num_machines[machine_type])
        for machine_type in num_machines
    }

    # Start breakdown processes
    for machine_type in machines:
        env.process(machines[machine_type].generate_breakdown())

    # Start raw material sending processes
    for product_type in PRODUCT_TYPES:
        env.process(send_raw_material(env, product_type, machines))

    # Start shift change process
    env.process(change_shift(env))

    # Run the simulation
    env.run(until=simulation_time)

    return PRODUCTS_PRODUCED, RAW_MATERIALS_USED


def perform_scenario_analysis(
    num_machines_list,
    shift_schedules_list,
    simulation_time=SIM_TIME,
):
    results = []
    for num_machines in num_machines_list:
        for shift_schedule in shift_schedules_list:
            env = simpy.Environment()
            products_produced, raw_materials_used = run_scenario(
                env, num_machines, shift_schedule, simulation_time
            )
            results.append(
                {
                    "Num_Machines": num_machines,
                    "Shift_Schedule": shift_schedule,
                    "Products_Produced": products_produced,
                    "Raw_Materials_Used": raw_materials_used,
                }
            )
    return results

# Example parameters for scenario analysis
num_machines_list = [
    {"Machining": 4, "Assembly": 7, "QualityControl": 2, "Packaging": 1},
    {"Machining": 5, "Assembly": 8, "QualityControl": 3, "Packaging": 2},
    {"Machining": 6, "Assembly": 9, "QualityControl": 4, "Packaging": 3},
]
shift_schedules_list = [
    {"Day": 15, "Evening": 10, "Night": 5},
    {"Day": 20, "Evening": 15, "Night": 10},
]

# Run the scenario analysis
results = perform_scenario_analysis(
    num_machines_list, shift_schedules_list
)

# Convert the results to a DataFrame and print
df = pd.DataFrame(results)
print(df)