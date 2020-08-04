age = int(input("Enter your Age (in years)"))
sex = input("Enter you Sex(M/F)")
if(sex == 'M'):
    if(age < 20):
        print("You are just a teen.")
    if(age >= 20 and age < 25):
        print("You are a young man now.")
    elif(age >=25 and age < 30):
        print("You are a mature man now")
    else:
        print("You are getting old")
if(sex == 'F'):
    if(age < 20):
        print("You are just a teen.")
    if(age >= 20 and age < 25):
        print("You are a young woman now.")
    elif(age >=25 and age < 30):
        print("You are a lady now")