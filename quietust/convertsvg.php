<?php
function convert_svg ($in, $out)
{
    if (filemtime($in) <= filemtime($out))
    {
        echo "$out is up to date, skipping.\n";
        return;
    }
    echo "Parsing $in...\n";
    $data = '';
    $raw = file_get_contents($in);
    $xml = new XMLReader();
    $xml->XML($raw);
    while (1)
    {
        $xml->read() or die('Unable to locate image data!');
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
foreach ($layers as $layer)
    convert_svg($layer .'.svg', $layer .'.dat');
?>


