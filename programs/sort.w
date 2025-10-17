
#modified selection sort

int n 5
array "3,4,1,2,5" nums
show nums


array "" sorted


int i 0
int elem 0
int min 0
int min_last 0

func set2
  elem = min
done

func set1
  if elem > min_last call set2
done

func find-min
  get nums i = elem
  i + 1 = i

  if elem < min call set1

  if i < n call find-min
done

int i2 0
while i2 < n
  0 = i
  i2 + 1 = i2
  1000000 = min

  call find-min
  push sorted min

  min = min_last
done


show sorted




