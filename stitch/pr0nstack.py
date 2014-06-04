#!/usr/bin/python

import os
import argparse        
import sys
import glob
import shutil
import subprocess

'''
zs should look something like:
#!/usr/bin/env bash
/home/mcmaster/document/software/zerene_stacker/ZereneStacker/run.sh "$@"

run.sh:
#!/bin/bash
appdir="$( cd "$( dirname "$0" )" && pwd )"
exten="$appdir"/JREextensions
chmod +x "${appdir}/jre/bin/java"
"${appdir}/jre/bin/java" -Xmx1024m -classpath "${appdir}/ZereneStacker.jar:${exten}/AppleShell.jar:${exten}/jai_codec.jar:${exten}/jai_core.jar:${exten}/jai_imageio.jar:${exten}/jdom.jar:${exten}/metadata-extractor-2.4.0-beta-1.jar" com.zerenesystems.stacker.gui.MainFrame "$@"
'''

def zs(in_xml,  out_dir, args):
    args.append("-batchScript")
    args.append(in_xml)

    args.append(out_dir)
    
    args = ['zs'] + args
    
    print 'Calling: %s' % (args,)
    
    subprocess.check_call(args, shell=False)


#  '%(a)d' % {'a':1}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Stack CNC output dirs into output dir')
    parser.add_argument('img_dirs_in', nargs='+', help='join images in input directories to form stacked output dir')
    parser.add_argument('img_dir_out', help='join images in input directories to form stacked output dir')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    
    if len(args.img_dirs_in) < 2:
        raise Exception('Require at leaste two dirs')
    
    out_fn = 'out.jpg'
    in_dirs = []
    fns = None
    # Verify all dirs have the same named files
    for d in args.img_dirs_in:
        if not os.path.isdir(d):
            raise Exception('Not a dir: %s' % (d,))
        dfns = glob.glob(os.path.join(d, '*.jpg'))
        dfns_base = [os.path.basename(fn) for fn in dfns]
        if fns is None:
            fns = dfns_base
        else:
            if fns != dfns_base:
                print fns
                print dfns_base
                raise Exception('Dirs not equal')
    print 'Found %d image sets to stack w/ %d images in each stack' % (len(fns), len(args.img_dirs_in))

    tmp_dir = '/tmp/pr0nstack.tmp'
    print 'Temp dir: %s' % tmp_dir
    # can't be in an image input dir or it will be tried to process as an image
    in_xml_fn = tmp_dir + '_in.xml'
    print 'in XML: %s' % in_xml_fn

    if os.path.exists(args.img_dir_out):
        if not args.force:
            raise Exception("Must set force to override output")
        shutil.rmtree(args.img_dir_out)
    os.mkdir(args.img_dir_out)

    for fn in fns:
        print
        print
        print
        
        srcs = [os.path.join(d, fn) for d in args.img_dirs_in]
        dst = os.path.join(args.img_dir_out, fn)
        print 'srcs: %s' % (srcs,)
        print 'dst: %s' % (dst,)

        srcs = [os.path.realpath(src) for src in srcs]

        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        os.mkdir(tmp_dir)

        '''
        There seems to be a bug where if the input folder contains a symbolic link it will successfully stack the image but fail to save it
        so instead we copy them now
        '''
        '''
        for i, src in enumerate(srcs):
            srcl = '%02d_%s.jpg' % (i, os.path.basename(os.path.dirname(src)))
            link = os.path.join(tmp_dir, srcl)
            print 'Linking %s => %s' % (link, src)
            os.symlink(src, link)
        '''

        for i, src in enumerate(srcs):
            srcl = '%02d_%s.jpg' % (i, os.path.basename(os.path.dirname(src)))
            link = os.path.join(tmp_dir, srcl)
            print 'Copying %s => %s' % (link, src)
            shutil.copy(src, link)
        
        #<OutputImagesDesignatedFolder value="%(out_dir)s" />
        # <BatchFileChooser.LastDirectory value="%(in_dir)s" />
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
<ZereneStackerBatchScript>
  <BatchQueue>
    <Batches length="1">
      <Batch>
        <Sources length="1">
          <Source value="%%CurrentProject%%" />
        </Sources>
        <ProjectDispositionCode value="101" />
        <Tasks length="1">
          <Task>
            <OutputImageDispositionCode value="2" />
            <Preferences>
              <AcquisitionSequencer.BacklashMillimeters value="0.22" />
              <AcquisitionSequencer.CommandLogging value="false" />
              <AcquisitionSequencer.DistancePerStepperRotation value="1.5875" />
              <AcquisitionSequencer.MaximumMmPerSecond value="2.0" />
              <AcquisitionSequencer.MicrostepsPerRotation value="3200" />
              <AcquisitionSequencer.MovementRampTime value="2.0" />
              <AcquisitionSequencer.NumberOfSteps value="5" />
              <AcquisitionSequencer.PrecisionThreshold value="0.05" />
              <AcquisitionSequencer.PrerunMillimeters value="0.0" />
              <AcquisitionSequencer.RPPIndicatorLeft value="-100.0" />
              <AcquisitionSequencer.RPPIndicatorRight value="+100.0" />
              <AcquisitionSequencer.SettlingTime value="3.0" />
              <AcquisitionSequencer.ShutterActivationsPerStep value="1" />
              <AcquisitionSequencer.ShutterAfterTime value="2.0" />
              <AcquisitionSequencer.ShutterBetweenTime value="1.0" />
              <AcquisitionSequencer.ShutterPulseTime value="0.3" />
              <AcquisitionSequencer.StepSize value="0.1" />
              <AcquisitionSequencer.StepSizeAdjustmentFactor value="1.0" />
              <AcquisitionSequencer.StepSizesFile value="" />
              <AlignmentControl.AddNewFilesAsAlreadyAligned value="false" />
              <AlignmentControl.AlignmentSettingsChanged value="false" />
              <AlignmentControl.AllowRotation value="true" />
              <AlignmentControl.AllowScale value="true" />
              <AlignmentControl.AllowShiftX value="true" />
              <AlignmentControl.AllowShiftY value="true" />
              <AlignmentControl.BrightnessSettingsChanged value="false" />
              <AlignmentControl.CorrectBrightness value="true" />
              <AlignmentControl.MaxRelDegRotation value="20" />
              <AlignmentControl.MaxRelPctScale value="20" />
              <AlignmentControl.MaxRelPctShiftX value="20" />
              <AlignmentControl.MaxRelPctShiftY value="20" />
              <AlignmentControl.Order.Automatic value="true" />
              <AlignmentControl.Order.NarrowFirst value="true" />
              <AllowReporting.UsageStatistics value="false" />
              <ColorManagement.DebugPrintProfile value="false" />
              <ColorManagement.InputOption value="Use_EXIF_and_DCF_rules" />
              <ColorManagement.InputOption.AssumedProfile value="sRGB IEC61966-2.1" />
              <ColorManagement.ManageZSDisplays value="false" />
              <ColorManagement.ManageZSDisplaysHasChanged value="false" />
              <ColorManagement.OutputOption value="CopyInput" />
              <DepthMapControl.AlgorithmIdentifier value="1" />
              <DepthMapControl.ContrastThresholdLevel value="5.2495434E-6" />
              <DepthMapControl.ContrastThresholdPercentile value="30.0" />
              <DepthMapControl.EstimationRadius value="10" />
              <DepthMapControl.SaveDepthMapImage value="false" />
              <DepthMapControl.SaveDepthMapImageDirectory value="" />
              <DepthMapControl.SaveUsedPixelImages value="false" />
              <DepthMapControl.SmoothingRadius value="5" />
              <DepthMapControl.UseFixedContrastThresholdLevel value="true" />
              <DepthMapControl.UseFixedContrastThresholdPercentile value="false" />
              <DepthMapControl.UsedPixelFractionThreshold value="0.5" />
              <FileIO.UseExternalTIFFReader value="false" />
              <Interpolator.RenderingSelection value="Interpolator.Spline4x4" />
              <Interpolator.ShowAdvanced value="false" />
              <LightroomPlugin.CurrentInstallationFolder value="" />
              <LightroomPlugin.DefaultColorSpace value="AdobeRGB" />
              <OutputImageNaming.Template value="ZS-OutputImage" />
              <Precrop.LimitsString value="" />
              <Precrop.Selected value="false" />
              <Prerotation.Degrees value="0" />
              <Prerotation.Selected value="false" />
              <Presize.UserSetting.Scale value="1.0" />
              <Presize.UserSetting.Selected value="false" />
              <Presize.Working.Scale value="1.0" />
              <PyramidControl.GritSuppressionMethod value="1" />
              <PyramidControl.RetainUDRImage value="false" />
              <RetouchingBrush.Hardness value="0.5" />
              <RetouchingBrush.ShowBrushes value="false" />
              <RetouchingBrush.Type value="Details" />
              <RetouchingBrush.Width value="10" />
              <SaveImage.BitsPerColor value="8" />
              <SaveImage.CompressionQuality value="0.75" />
              <SaveImage.FileType value="jpg" />
              <SaveImage.RescaleImageToAvoidOverflow value="false" />
              <SkewSequence.FirstImage.MaximumShiftXPct value="-3.0" />
              <SkewSequence.FirstImage.MaximumShiftYPct value="0.0" />
              <SkewSequence.LastImage.MaximumShiftXPct value="3.0" />
              <SkewSequence.LastImage.MaximumShiftYPct value="0.0" />
              <SkewSequence.NumberOfOutputImages value="3" />
              <SkewSequence.Selected value="false" />
              <StackingControl.FrameSkipFactor value="1" />
              <StackingControl.FrameSkipSelected value="false" />
              <StereoOrdering.LeftRightIndexSeparation value="1" />
              <WatchDirectoryOptions.AcceptViaDelay value="false" />
              <WatchDirectoryOptions.AcceptViaDelaySeconds value="2.0" />
            </Preferences>
            <TaskIndicatorCode value="2" />
          </Task>
        </Tasks>
      </Batch>
    </Batches>
  </BatchQueue>
</ZereneStackerBatchScript>''' % {'out_dir':tmp_dir, 'in_dir':tmp_dir}
        open(in_xml_fn, 'w').write(xml + '\n\n')
        zs(in_xml_fn,  tmp_dir, ["-noSplashScreen", "-exitOnBatchScriptCompletion", "-runMinimized", "-showProgressWhenMinimized=false"])
        
        outfns = glob.glob(os.path.join(tmp_dir, 'ZS-OutputImage*.jpg'))
        if len(outfns) != 1:
            print outfns
            raise Exception('Missing output image')
        stacked_src = outfns[0]
        stacked_dst = os.path.join(args.img_dir_out, fn)
        print 'Moving stacked image %s => %s' % (stacked_src, stacked_dst)
        shutil.move(stacked_src, stacked_dst)
        shutil.rmtree(tmp_dir)
        print '%s complete' % (fn,)
