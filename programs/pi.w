
# pi approximation

int pi4 0.0

int i 0.0
int sign 1.0

int k2 0.0
int k21 0.0
int ik21 0.0

func iter
  i * 2 = k2
  k2 + 1 = k21
  1 / k21 = ik21

  ik21 * sign = ik21
  sign * -1   = sign

  ik21 + pi4 = pi4
  i + 1 = i
done

#bypass loop limit lol
int i100 0
func bypass
  i100 + 1 = i100

  call iter

  if i100 < 100 call bypass
done

while i < 100000
  0 = i100
  call bypass
  show i
done
  
  
  

int pi 0.0
pi4 * 4 = pi


show pi






