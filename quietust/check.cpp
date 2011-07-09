/*
Copyright 2011 Quietust
Released under 2 clause BSD license, see COPYING for details
Minor modifications by John McMaster <JohnDMcMaster@gmail.com>
*/

#include <stdio.h>
#include "polygon.h"
#include "files.h"

void help(const char *prog_name) {
	printf("%s: run design rule check (DRC)\n", prog_name);
	printf("Usage: %s\n", prog_name);
	printf("(no args...yet)\n");
	printf("Input files:\n");
	printf("\t%s\n", DAT_FILE_METAL_VCC);
	printf("\t%s\n", DAT_FILE_METAL_GND);
	printf("\t%s\n", DAT_FILE_METAL);
	printf("\t%s\n", DAT_FILE_POLYSILICON);
	printf("\t%s\n", DAT_FILE_DIFFUSION);
	printf("\t%s\n", DAT_FILE_VIAS);
	printf("\t%s\n", DAT_FILE_BURIED_CONTACTS);
}

int main (int argc, char **argv)
{
	vector<node *> nodes, vias;
	node *via, *cur;

	unsigned int metal_start, metal_end;
	unsigned int poly_start, poly_end;
	unsigned int diff_start, diff_end;
	
	if (argc > 1) {
		help(argv[0]);
		exit(1);
	}
	
	readnodes<node>(DAT_FILE_METAL_VCC, nodes, LAYER_METAL);
	if (nodes.size() != 1)
	{
		fprintf(stderr, "Error: VCC plane contains more than one node!\n");
		return 1;
	}
	readnodes<node>(DAT_FILE_METAL_GND, nodes, LAYER_METAL);
	if (nodes.size() != 2)
	{
		fprintf(stderr, "Error: GND plane contains more than one node!\n");
		return 1;
	}
	metal_start = nodes.size();
	readnodes<node>(DAT_FILE_METAL, nodes, LAYER_METAL);
	metal_end = poly_start = nodes.size();
	readnodes<node>(DAT_FILE_POLYSILICON, nodes, LAYER_POLY);
	poly_end = diff_start = nodes.size();
	readnodes<node>(DAT_FILE_DIFFUSION, nodes, LAYER_DIFF);
	diff_end = nodes.size();

	readnodes<node>(DAT_FILE_VIAS, vias, LAYER_SPECIAL);

	printf("Checking for bad vias (%i total)\n", vias.size());
	for (unsigned int i = 0; i < vias.size(); i++)
	{
//		printf("%i     \r", i);
		int hits = 0;
		via = vias[i];
		// not metal_start - we need to include the power planes
		for (unsigned int j = 0; j < diff_end; j++)
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

	readnodes<node>(DAT_FILE_BURIED_CONTACTS, vias, LAYER_SPECIAL);

	printf("Checking for bad buried contacts (%i total)\n", vias.size());
	for (unsigned int i = 0; i < vias.size(); i++)
	{
//		printf("%i     \r", i);
		int hits = 0;
		via = vias[i];
		for (unsigned int j = poly_start; j < diff_end; j++)
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
