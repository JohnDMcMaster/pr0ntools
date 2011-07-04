/*
Copyright 2011 Quietust
Released under 2 clause BSD license, see COPYING for details
*/

#include <stdio.h>
#include "polygon.h"

int main (int argc, char **argv)
{
	vector<node *> nodes, vias;
	node *via, *cur;
	int j;

	int metal_start, metal_end;
	int poly_start, poly_end;
	int diff_start, diff_end;
	readnodes<node>("metal_vcc.dat", nodes, LAYER_METAL);
	if (nodes.size() != 1)
	{
		fprintf(stderr, "Error: VCC plane contains more than one node!\n");
		return 1;
	}
	readnodes<node>("metal_gnd.dat", nodes, LAYER_METAL);
	if (nodes.size() != 2)
	{
		fprintf(stderr, "Error: GND plane contains more than one node!\n");
		return 1;
	}
	metal_start = nodes.size();
	readnodes<node>("metal.dat", nodes, LAYER_METAL);
	metal_end = poly_start = nodes.size();
	readnodes<node>("polysilicon.dat", nodes, LAYER_POLY);
	poly_end = diff_start = nodes.size();
	readnodes<node>("diffusion.dat", nodes, LAYER_DIFF);
	diff_end = nodes.size();

	readnodes<node>("vias.dat", vias, LAYER_SPECIAL);

	printf("Checking for bad vias (%i total)\n", vias.size());
	for (unsigned int i = 0; i < vias.size(); i++)
	{
//		printf("%i     \r", i);
		int hits = 0;
		via = vias[i];
		// not metal_start - we need to include the power planes
		for (j = 0; j < diff_end; j++)
		{
			cur = nodes[j];
			if (cur->collide(via))
				hits++;
		}
		if (hits == 2)
			continue;
		if (hits == 1)
			printf("Via %i (%s) goes to nowhere!\n", i, via->poly.toString().c_str());
		else	printf("Via %i (%s) connects to more than 2 nodes (found %i)!\n", i, via->poly.toString().c_str(), hits);
	}

	vias.clear();

	readnodes<node>("buried_contacts.dat", vias, LAYER_SPECIAL);

	printf("Checking for bad buried contacts (%i total)\n", vias.size());
	for (unsigned int i = 0; i < vias.size(); i++)
	{
//		printf("%i     \r", i);
		int hits = 0;
		via = vias[i];
		for (j = poly_start; j < diff_end; j++)
		{
			cur = nodes[j];
			if (cur->collide(via))
				hits++;
		}
		if (hits == 2)
			continue;
		if (hits == 1)
			printf("Buried contact %i (%s) goes to nowhere!\n", i, via->poly.toString().c_str());
		else	printf("Buried contact %i (%s) connects to more than 2 nodes (found %i)!\n", i, via->poly.toString().c_str(), hits);
	}
	vias.clear();
	printf("Done!\n");
}
