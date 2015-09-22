



if __name__ == "__main__":
    print "Starting to parse latencies..."
    fo = open("netflix10.log", "r")
    print "Name of the file: ", fo.name

    f_mean = open("stats_mean.csv", "w")
    f_median = open("stats_median.csv", "w")
    f_nintyfive = open("stats_nintyfive.csv", "w")
    f_all = open("stats_all.csv", "w")

    
    for line in fo.readlines():
        parts = line.split(",")
        mean = parts[5]
        f_mean.write(mean + "\n")

        median = parts[6]
        f_median.write(median + "\n")
        nintyfive = parts[7]
        f_nintyfive.write(nintyfive + "\n")


        f_all.write("{},{},{}\n".format(mean,median, nintyfive))

