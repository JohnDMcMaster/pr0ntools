/*
Visual 2A03 Netlist Generator
Copyright 2011 Quietust
Released under 2 clause BSD license, see COPYING for details
*/

#include <stdio.h>
#include "polygon.h"

#include <vector>
using namespace std;

int main (int argc, char **argv)
{
	vector<node *> nodes;
	vector<transistor *> transistors;
	
	unsigned int metal_start, metal_end;
	unsigned int poly_start, poly_end;
	unsigned int diff_start, diff_end;
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

	int vcc = 10000;
	int gnd = 10001;
	int nextNode = 10002;

	vector<node *> vias, matched, unmatched;
	node *via, *cur, *sub;

	readnodes<node>("vias.dat", vias, LAYER_SPECIAL);

	printf("Parsing VCC plane - %i vias remaining\n", vias.size());
	{
		cur = nodes[0];
		cur->id = vcc;
		for (unsigned int i = 0; i < vias.size(); i++)
		{
			via = vias[i];
			if (cur->collide(via))
				matched.push_back(via);
			else	unmatched.push_back(via);
		}
		while (!matched.empty())
		{
//			printf("%i    \r", matched.size());
			via = matched.back();
			matched.pop_back();
			for (unsigned int i = poly_start; i < diff_end; i++)
			{
				sub = nodes[i];
				if (sub->collide(via))
				{
					delete via;
					via = NULL;
					sub->id = vcc;
					break;
				}
			}
			if (via)
				unmatched.push_back(via);
		}
		vias = unmatched;
		unmatched.clear();
	}

	printf("Parsing GND plane - %i vias remaining\n", vias.size());
	{
		cur = nodes[1];
		cur->id = gnd;
		for (unsigned int i = 0; i < vias.size(); i++)
		{
			via = vias[i];
			if (cur->collide(via))
				matched.push_back(via);
			else	unmatched.push_back(via);
		}
		while (!matched.empty())
		{
//			printf("%i    \r", matched.size());
			via = matched.back();
			matched.pop_back();
			for (unsigned int i = poly_start; i < diff_end; i++)
			{
				sub = nodes[i];
				if (sub->collide(via))
				{
					delete via;
					via = NULL;
					sub->id = gnd;
					break;
				}
			}
			if (via)
				unmatched.push_back(via);
		}
		vias = unmatched;
		unmatched.clear();
	}

	printf("Parsing metal nodes %i thru %i - %i vias remaining\n", metal_start, metal_end - 1, vias.size());
	for (unsigned int i = metal_start; i < metal_end; i++)
	{
//		printf("%i        \r", i);
		cur = nodes[i];
		if (!cur->id)
			cur->id = nextNode++;
		for (unsigned int j = 0; j < vias.size(); j++)
		{
			via = vias[j];
			if (cur->collide(via))
				matched.push_back(via);
			else	unmatched.push_back(via);
		}
		while (!matched.empty())
		{
//			printf("%i.%i\r", i, matched.size());
			via = matched.back();
			matched.pop_back();
			for (unsigned int j = poly_start; j < diff_end; j++)
			{
				sub = nodes[j];
				if (sub->collide(via))
				{
					delete via;
					via = NULL;
					if (sub->id == 0)
						sub->id = cur->id;
					else if (sub->id != cur->id)
					{
//						if (cur->id == (nextNode - 1))
//							nextNode--;
						int oldid = cur->id;
						int newid = sub->id;
						for (unsigned int k = 0; k < nodes.size(); k++)
							if (nodes[k]->id == oldid)
								nodes[k]->id = newid;
					}
					break;
				}
			}
			if (via)
				unmatched.push_back(via);
		}
		vias = unmatched;
		unmatched.clear();
	}
	if (!vias.empty())
	{
		printf("%i vias were not matched!\n", vias.size());
		while (!vias.empty())
		{
			via = vias.back();
			vias.pop_back();
			fprintf(stderr, "Via (%s) was not hit!\n", via->poly.toString().c_str());
			delete via;
		}
	}

	readnodes<node>("buried_contacts.dat", vias, LAYER_SPECIAL);

	printf("Parsing polysilicon nodes %i thru %i - %i buried contacts remaining\n", poly_start, poly_end - 1, vias.size());
	for (unsigned int i = poly_start; i < poly_end; i++)
	{
//		printf("%i        \r", i);
		cur = nodes[i];
		if (!cur->id)
			cur->id = nextNode++;
		for (unsigned int j = 0; j < vias.size(); j++)
		{
			if (cur->collide(vias[j]))
				matched.push_back(vias[j]);
			else	unmatched.push_back(vias[j]);
		}
		while (!matched.empty())
		{
//			printf("%i.%i\r", i, matched.size());
			via = matched.back();
			matched.pop_back();
			for (unsigned int j = diff_start; j < diff_end; j++)
			{
				sub = nodes[j];
				if (sub->collide(via))
				{
					delete via;
					via = NULL;
					if (sub->id == 0)
						sub->id = cur->id;
					else if (sub->id != cur->id)
					{
//						if (cur->id == (nextNode - 1))
//							nextNode--;
						int oldid = cur->id;
						int newid = sub->id;
						for (unsigned int k = 0; k < nodes.size(); k++)
							if (nodes[k]->id == oldid)
								nodes[k]->id = newid;
					}
					break;
				}
			}
			if (via)
				unmatched.push_back(via);
		}
		vias = unmatched;
		unmatched.clear();
		if (cur->id == gnd)
			cur->layer = LAYER_PROTECT;
	}
	if (!vias.empty())
	{
		printf("%i buried contacts were not matched!\n", vias.size());
		while (!vias.empty())
		{
			via = vias.back();
			vias.pop_back();
			fprintf(stderr, "Buried contact (%s) was not hit!\n", via->poly.toString().c_str());
			delete via;
		}
	}

	printf("Parsing diffusion nodes %i thru %i\n", diff_start, diff_end - 1);
	for (unsigned int i = diff_start; i < diff_end; i++)
	{
		cur = nodes[i];
		if (!cur->id)
			cur->id = nextNode++;
		if (cur->id == vcc)
			cur->layer = LAYER_DIFF_VCC;
		if (cur->id == gnd)
			cur->layer = LAYER_DIFF_GND;
	}

	readnodes<transistor>("transistors.dat", transistors, LAYER_SPECIAL);
	transistor *cur_t;
	nextNode = 10000;

	vector<int> diffs;
	int pullups = 0;

	node *t1 = new node;
	node *t2 = new node;
	node *t3 = new node;
	node *t4 = new node;

	printf("Parsing %i transistors\n", transistors.size());
	for (unsigned int i = 0; i < transistors.size(); i++)
	{
//		printf("%i     \r", i);
		cur_t = transistors[i];
		cur_t->id = nextNode++;
		for (unsigned int j = poly_start; j < poly_end; j++)
		{
			sub = nodes[j];
			if (sub->collide(cur_t))
			{
				cur_t->gate = sub->id;
				break;
			}
		}
		t1->poly = polygon(cur_t->poly);
		t2->poly = polygon(cur_t->poly);
		t3->poly = polygon(cur_t->poly);
		t4->poly = polygon(cur_t->poly);
		t1->poly.move(-4, 0);
		t2->poly.move(2, 0);
		t3->poly.move(0, -4);
		t4->poly.move(0, 2);
		t1->poly.bRect(t1->bbox);
		t2->poly.bRect(t2->bbox);
		t3->poly.bRect(t3->bbox);
		t4->poly.bRect(t4->bbox);
		for (unsigned int j = diff_start; j < diff_end; j++)
		{
			sub = nodes[j];
			if (sub->collide(t1) || sub->collide(t2) || sub->collide(t3) || sub->collide(t4))
				diffs.push_back(sub->id);
		}
		if (diffs.size() == 2)
		{
			cur_t->c1 = diffs[0];
			cur_t->c2 = diffs[1];

			// if the gate is connected to the 2nd terminal, swap the terminals around
			// the other one will probably end up being VCC or GND

			if (cur_t->c2 == cur_t->gate)
			{
				cur_t->c2 = cur_t->c1;
				cur_t->c1 = cur_t->gate;
			}
			// if the gate is connected to one terminal and the other terminal is VCC/GND, assign pullup state to the other side
			if (cur_t->c1 == cur_t->gate)
			{
				// gate == c1, c2 == VCC -> it's a pull-up resistor
				// but don't do this if the other side is GND!
				if ((cur_t->c2 == vcc) && (cur_t->c1 != gnd))
				{
					// assign pull-up state
					for (unsigned int j = metal_start; j < diff_end; j++)
					{
						if (nodes[j]->id == cur_t->gate)
							nodes[j]->pullup = '+';
					}
					// then discard the transistor
					cur_t->id = 0;
					nextNode--;
					pullups++;
				}
			}
		}
		else
		{
			// assign dummy values
			cur_t->c1 = gnd;
			cur_t->c2 = gnd;
			fprintf(stderr, "\rTransistor %i had wrong number of terminals (%i)\n", cur_t->id, diffs.size());
		}
		diffs.clear();
	}
	printf("%i transistors turned out to be pull-up resistors\n", pullups);

	delete t1;
	delete t2;
	delete t3;
	delete t4;

	for (unsigned int i = 0; i < transistors.size(); i++)
	{
		cur_t = transistors[i];
		cur_t->poly.move(-1, -1);
		cur_t->poly.bRect(cur_t->bbox);
	}

	FILE *out;

	printf("Writing transdefs.js\n");
	out = fopen("transdefs.js", "wt");
	if (!out)
	{
		fprintf(stderr, "Unable to create transdefs.js!\n");
		return 1;
	}
//	fprintf(out, "var transdefs = [\n");
	for (unsigned int i = 0; i < transistors.size(); i++)
	{
		cur_t = transistors[i];
		// skip pullups
		if (cur_t->id)
			fprintf(out, "['t%i',%i,%i,%i,[%i,%i,%i,%i]],\n", cur_t->id, cur_t->gate, cur_t->c1, cur_t->c2, cur_t->bbox.xmin, cur_t->bbox.xmax, cur_t->bbox.ymin, cur_t->bbox.ymax);
		delete cur_t;
	}
//	fprintf(out, "]\n");
	fclose(out);
	transistors.clear();

	printf("Writing segdefs.js\n");
	out = fopen("segdefs.js", "wt");
	if (!out)
	{
		fprintf(stderr, "Unable to create segdefs.js!\n");
		return 1;
	}
//	fprintf(out, "var segdefs = [\n");
	// skip the main VCC and GND nodes, since those are huge and we don't really need them
	for (unsigned int i = 2; i < nodes.size(); i++)
	{
		cur = nodes[i];
		fprintf(out, "[%i,'%c',%i,%s],\n", cur->id, cur->pullup, cur->layer, cur->poly.toString().c_str());
		delete cur;
	}
//	fprintf(out, "]\n");
	fclose(out);
	nodes.clear();

	printf("All done!\n");
	return 0;
}
