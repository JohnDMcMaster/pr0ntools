#!/usr/bin/env php
<?php
/*
Copyright 2011 Quietust
Released under 2 clause BSD license, see COPYING for details
Minor modifications by John McMaster <JohnDMcMaster@gmail.com>
*/

function convert_svg ($in, $out)
{
	# Hmm this is what make is for...might remove
	if (file_exists($out)) {
		if (filemtime($in) <= filemtime($out))
		{
		    echo "$out is up to date, skipping.\n";
		    return;
		}
	}
    echo "Parsing $in...\n";
    $data = '';
	//Apparantly SVG files are pure XML
    $raw = file_get_contents($in);

	/*
    echo '\n';
    echo $raw;
    echo '\n';
    */
    
    $xml = new XMLReader();
    $xml->XML($raw);
    while (1)
    {
		/*
		libxml_use_internal_errors(true);
        if (!$xml->read() && false) {
        	print "Read failed\n";
			$errors = libxml_get_errors();
			print $errors . ", " . count($errors) . "\n";
			foreach ($errors as $error) {
        		// handle errors here
				print "error: " . $error . "\n";
			}
			libxml_clear_errors();
        	//print xml_error_string(xml_get_error_code($xml)) . "\n";
			die("Unable to locate image data!\n");
		}
		*/
		$xml->read() or die("Unable to locate image data!\n");
		print $xml->name . "\n";
        if ($xml->name != 'path')
            continue;
        $raw = $xml->getAttribute('d');
        break;
    }
    $raw = preg_split('/[\s]+/', $raw);
    $i = 0;
    $cmd = $raw[$i++];
    while ($i < count($raw))
    {
        switch ($cmd)
        {
        case 'M':
            $lastpt = $raw[$i++];
            $cmd = $raw[$i++];
            break;
        case 'C':
            $pt1 = $raw[$i++];
            if ($pt1 == 'Z')
            {
                $data .= "-1,-1\n";
                if ($i < count($raw))
                    $cmd = $raw[$i++];
            }
            else
            {
                $pt2 = $raw[$i++];
                $pt3 = $raw[$i++];
                if (($lastpt != $pt1) || ($pt2 != $pt3))
                    echo "Curve detected at $pt1! Please fix and re-export.\n";
                $data .= str_replace('.00', '', $pt3)."\n";
                $lastpt = $pt3;
            }
            break;
        default:
            die("Unknown command $cmd!");
        }
    }
    file_put_contents($out, $data);
}

if (count($argv) > 1) {
	$layers = array_slice($argv, 1);
} else {
	//Original hard coded file list	
	$layers = array(
		'metal_vcc',
		'metal_gnd',
		'metal',
		'vias',
		'polysilicon',
		'buried_contacts',
		'diffusion',
		'transistors',
	);
}

//Pre-check that all files are present
$abort = false;
foreach ($layers as $layer) {
	$src_file_name = $layer .'.svg';
	if (!file_exists($src_file_name)) {
		print 'File ' . $src_file_name . " is missing\n";
		$abort = true;
	}
}
if ($abort) {
	print "Errors, aborting\n";
	exit(1);
}

foreach ($layers as $layer) {
	$src_file_name = $layer .'.svg';
	$dst_file_name = $layer .'.dat';
    convert_svg($src_file_name, $dst_file_name);
}
?>


