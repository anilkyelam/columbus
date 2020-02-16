



def validate(r,c):
	if(r > row_len-1 or r < 0 or c > col_len-1 or c < 0):
		return False
	else:
		return (r,c)

def get_neighbours(r,c):
	directions = [(r-1,c), (r+1,c), (r,c-1), (r, c+1)]
	valid = [validate(p[0],p[1]) for p in directions]
	max_carrots = 0
	for i in range(4):
		if(valid[i]):
			r = directions[i][0]
			c = directions[i][1]
			if(max_carrots < l[r][c]):
				max_carrots = l[r][c]
	return max_carrots

with open('matrix.txt', 'r') as f:
    l = [[int(num) for num in line.split(',')] for line in f]
row_len = len(l)
col_len = len(l[0])
mid_cell_row_ind = row_len/2
mid_cell_col_ind = col_len/2
print (mid_cell_col_ind)
print (mid_cell_row_ind)
carrots=0
current_r = mid_cell_row_ind
current_c = mid_cell_col_ind
while(l[current_r][current_c]!=0):
	carrots += l[current_r][current_c]
	next_carrot = get_neighbours(current_r, current_c)
	if(next_carrot==0):
		print(carrots)
		break



