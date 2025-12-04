#!/usr/bin/env python
import numpy as np
import matplotlib.pyplot as plt

def makePrices(price0, nsteps=100, seed=None):
	if seed != None:
		np.random.seed(seed)
	prices = [price0]
	for i in range(nsteps):
		prices.append(prices[-1] + np.random.randint(-1, 2))  # high not inclusive

	return prices

def movingAvg(prices, width, step=1):
	avgs = []
	for i in range(len(prices)-width):
		s = prices[i:i+width]
		m = np.average(s)
		avgs.append(m)
	return avgs

def doAction(prices, mvavgs, width, cash0=100, stock0=0):
	cash, stock = cash0, stock0
	for i in range(len(mvavgs)):
		p = prices[i+width]
		m = mvavgs[i]
		if p < m and cash > 0:
			stock += cash//2
			cash -= cash//2
		elif p > m and stock > 0:
			stock -= stock//2
			cash += stock//2

		if cash == 0:
			break

	return cash0 + stock0, cash + stock

if __name__ == '__main__':
	prices = makePrices(100, 1000)
	xvals = np.arange(len(prices))
	mvavgs = movingAvg(prices, 25)
	plt.plot(xvals, prices)
	plt.plot(xvals[25:], mvavgs)
	plt.show()
	initial, final = doAction(prices, mvavgs, 25)
	print(initial, final)
