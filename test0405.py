rx = """1713 4324 
2017 2168 
2015 2168 
2014 2173 
2016 2175 
2019 32"""
sa = "hello"
rx = rx.partition('\n')[2:]
sa = sa.split('\n')
# rx = rx[:rx.rfind('\r\n')-3]
print(rx)