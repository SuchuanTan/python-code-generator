from tla_reviewer.tla_reviewer import validate_tla
from code_testbench_generator.code_testbench_generator import generate_with_retry
from code_executor.code_executor import PythonExecutor

requirement = input("Please enter your requirement: ：")
# TODO:添加重试机制
retries = 0
MAX_RETRIES = 3
# TODO: 生成TLA, 检查TLA
tla = "Add(a, b) == a + b"
vali_res = validate_tla(requirement=requirement, tla_spec=tla)
print("TLA+ Reviewing Result:")
print("Success" if vali_res.success else "Failure")
print("Reason: " + vali_res.reason)

gen_res = generate_with_retry(requirement=requirement, tla_spec=tla)
code = gen_res.code
print("Generation Result:")
print("Success" if gen_res.success else "Failure")
print()

executor = PythonExecutor()
execute_res = executor.run(code)
print(execute_res)
if(execute_res.success):
    print("Result: ", "Success")
    print("Output: ", execute_res.output or "N/A")
else:
    print("Result: ", "Failure")
    print("Output: ", execute_res.output or "N/A")
    print("Exception Type: " + execute_res.exception_type or "N/A")
    print("Error: " + execute_res.error or "N/A")

