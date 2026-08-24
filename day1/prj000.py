#### 定義函式 ####


# 沒有輸入值, 沒有返回值
def print_hello():
    print("hello")


# 有輸入值, 沒有返回值
def print_hello_name(name):
    print("hello " + name)


# 有輸入值, 有返回值
def get_hello_name(num1, num2):
    return num1 + num2


##### 使用函式 #####


print_hello()  # 沒有輸入值, 沒有返回值


print_hello_name("Yun-Tse")  # 有輸入值, 沒有返回值


a = get_hello_name(1, 1)  # 有輸入值, 有返回值
print(f"答案是{a}")  # 返回值的列印(要先把返回值存成變數，否則會error)
