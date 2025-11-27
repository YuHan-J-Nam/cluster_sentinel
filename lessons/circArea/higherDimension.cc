// Coded in C++

#include <iostream>
#include <cstdlib>
#include <cmath>
#include <cstddef>
using namespace std;

int main()
{
	const double r = 1;
	const int nDim = 37;
	const double aSqr = pow((2*r), nDim);

	long nAccept = 0;
	long nTotal = 100000;

	for ( int i=0; i<nTotal; ++i) {
		double rNewSq = 0;
		for ( int d=0; d<nDim; ++d ) {
			const double xi = r*(2*double(rand())/RAND_MAX - 1);
			rNewSq += xi*xi;
		}
		const double rNew = sqrt(rNewSq);

		if ( rNew <= r ) {
			nAccept += 1;
		}
	}

	const double area = aSqr * nAccept / nTotal;
	cout << area << endl; // This is the python equivalent of printf("%f", area);

	return 0;
}
