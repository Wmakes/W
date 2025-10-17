show "Hello W 0.9.1"        # 1 - Version update
int negative -5           # 2 - Test negative number
show negative             # 3 - Display negative
int  myNumber 42           # 4
show myNumber            # 5
array "-1,-2,3" myArray # 6 - Array with negatives
show myArray       # 7
3+2=sum               # 8
show sum              # 9
4-1=difference           # 10
show difference           # 11
-6*7=negativeProduct     # 12 - Test negative multiplication
show negativeProduct     # 13
8/ -2=negativeQuotient     # 14 - Division with negative
show negativeQuotient      # 15
if negative < "0" show "Negative OK"  # 16 - Condition with negative
if myNumber = "42" show "myNumber = 42"  # 17
if myNumber != "42" show "FAIL" else show "myNumber != 42"  # 18
2+3=sum               # 19
show sum              # 20
leng myArray       # 21
show "Array length:"  # 22
push myArray "-99"   # 23 - Push negative
show myArray       # 24
pop myArray        # 25
show myArray      # 26
func myFunction       # 27
show "Hello from function"   # 28
done                     # 29
call myFunction       # 30
input "Enter something:" = input  # 31
show input           # 32
time                     # 33
show "Time in seconds:" # 34
date                     # 35
show "Date:"             # 36
datetime                 # 37
show "Date and time:"   # 38
show "We will stop the program for 2 seconds"  # 39
sleep 2                  # 40
show "Continuing"      # 41
random -5 5 = random      # 42 - Test random negative range
show "Test random -5-5:" # 43
show random               # 44
write "Hello W to file!" "file.txt"  # 45
read "file.txt" =  read # 46
show read            # 47
int a 5                 # 48
int b 10                # 49
show a                 # 50
show b                 # 51
int counter 0          # 52
while counter < 5      # 53
show counter           # 54
counter + 1 = counter # 55
done                     # 56
bool isOK true           # 57 - Boolean variable
bool notOK false         # 58 - Boolean variable
show isOK            # 59- Should display True
show notOK             # 60 - Should display False
if isOK and notOK = false show "Logic and works"  # 61
if isOK or notOK = true show "Logic or works"   # 62
if not notOK show "Not works"  # 63 - Condition with not
array_str "alex","has","cat" words  # 64 - String list
show words             # 65 - Should display ['alex', 'has', 'cat']
get words "1" = result  # 66 - Get 'has'
show result             # 67 - Should display 'has'
get myArray "1" = result2  # 68 - Get -2
show result2         # 69 - Should display -2
int x 0              # 70
int y 1              # 71
func while-test      # 72
while x < 2          # 73
x + y = x            # 74
show x               # 75
done                 # 76
done                 # 77
call while-test      # 78
END                  # 79
show result2         # 80
