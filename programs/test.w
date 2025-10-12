show "Hello W 0.8.1"        # 1 - Version update
int -5 'negative'           # 2 - Test negative number
show 'negative'             # 3 - Display negative
int 42 'myNumber'          # 4
show 'myNumber'            # 5
array -1,-2,3 'myArray' # 6 - Array with negatives
show 'myArray'       # 7
3+2='sum'               # 8
show 'sum'              # 9
4-1='difference'            # 10
show 'difference'           # 11
-6*7='negativeProduct'     # 12 - Test negative multiplication
show 'negativeProduct'     # 13
8/ -2='negativeQuotient'     # 14 - Division with negative
show 'negativeQuotient'      # 15
if 'negative' < 0 show "Negative OK"  # 16 - Condition with negative
if 'myNumber' = 42 show "myNumber = 42"  # 17
if 'myNumber' != 42 show "FAIL" else show "myNumber != 42"  # 18
int 0 'counter'          # 19 - Replace redo
while 'counter' < 3      # 20 - While loop instead of redo
show "repeating 3 times"  # 21
'counter' + 1 ='counter' # 22
done                     # 23
2+3='sum'               # 24
show 'sum'              # 25
show 'sum'              # 26
leng 'myArray'       # 27
show "Array length:"  # 28
push 'myArray' -99   # 29 - Push negative
show 'myArray'       # 30
pop 'myArray'        # 31
show 'myArray'       # 32
func 'myFunction'       # 33
show "Hello from function"   # 34
done                     # 35
call 'myFunction'       # 36
input "Enter something:" = 'input'  # 37
show 'input'           # 38
time                     # 39
show "Time in seconds:" # 40
date                     # 41
show "Date:"             # 42
datetime                 # 43
show "Date and time:"   # 44
show "We will stop the program for 2 seconds"  # 45
sleep 2                  # 46
show "Continuing"      # 47
random -5 5 = 'random'      # 48 - Random with negative start
show "Test random -5-5:" # 49
show 'random'               # 50
write "Hello W to file!" "file.txt"  # 51
read "file.txt" 'read' # 52
show 'read'            # 53
int 5 'a'                # 54
int 10 'b'               # 55
show 'a'                 # 56
show 'b'                 # 57
int 0 'counter'          # 58
while 'counter' < 5      # 59
show 'counter'           # 60
'counter' + 1 ='counter' # 61
done                     # 62
bool true 'isOK'       # 63 - Bool declaration
bool false 'notOK'       # 64
show 'isOK'            # 65 - Should display True
show 'notOK'             # 66 - Should display False
if 'isOK' and 'notOK' = false show "Logic and works"  # 67
if 'isOK' or 'notOK' = true show "Logic or works"   # 68
if not 'notOK' show "Not works"  # 69 - Condition with not
array_str "ala","has","cat" 'words'  # 70 - String list
show 'words'             # 71 - Should display ['ala', 'has', 'cat']
get 'words' 1 = 'result'  # 72 - Get 'has'
show 'result'             # 73 - Should display 'has'
get 'myArray' 1 = 'result2'  # 74 - Get -2
show 'result2'           # 75 - Should display -2
END                     # 76
show 'result2'           # 77
