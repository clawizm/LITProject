import itertools


all_on_leds = [[(0, 32), (32, 64)], []]
print(list(itertools.chain.from_iterable(all_on_leds)))