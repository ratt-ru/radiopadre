#!/usr/bin/env python

'''
Run script with desired B tables
Requirement: bokeh
'''
import pdb
#import matplotlib
#matplotlib.use('Agg')
from pyrap.tables import table
from optparse import OptionParser
import matplotlib.colors as colors
import matplotlib.cm as cmx
import glob
import numpy
import pylab
import sys
import numpy as np

from bokeh.plotting import figure
from bokeh.models import Range1d, HoverTool
from bokeh.io import output_file, show
from bokeh.layouts import row, column


#output_file('B_tables_bokeh.html')


parser = OptionParser(usage='%prog [options] tablename')
parser.add_option('-f','--field',dest='field',help='Field ID to plot (default = 0)',default=0)
parser.add_option('-d','--doplot',dest='doplot',help='Plot complex values as amp and phase (ap) or real and imag (ri) (default = ap)',default='ap')
parser.add_option('-a','--ant',dest='plotants',help='Plot only this antenna, or comma-separated list of antennas',default=[-1])
parser.add_option('-c','--corr',dest='corr',help='Correlation index to plot (usually just 0 or 1, default = 0)',default=0)
parser.add_option('--t0',dest='t0',help='Minimum time to plot (default = full range)',default=-1)
parser.add_option('--t1',dest='t1',help='Maximum time to plot (default = full range)',default=-1)
parser.add_option('--yu0',dest='yu0',help='Minimum y-value to plot for upper panel (default = full range)',default=-1)
parser.add_option('--yu1',dest='yu1',help='Maximum y-value to plot for upper panel (default = full range)',default=-1)
parser.add_option('--yl0',dest='yl0',help='Minimum y-value to plot for lower panel (default = full range)',default=-1)
parser.add_option('--yl1',dest='yl1',help='Maximum y-value to plot for lower panel (default = full range)',default=-1)
parser.add_option('--cmap',dest='mycmap',help='Matplotlib colour map to use for antennas (default = coolwarm)',default='coolwarm')
parser.add_option('--size',dest='mysize',help='Font size for figure labels (default = 20)',default=20)
parser.add_option('--ms',dest='myms',help='Measurement Set to consult for proper antenna names',default='')
parser.add_option('-p','--plotname',dest='pngname',help='Output PNG name (default = something sensible)',default='')
(options,args) = parser.parse_args()


field = int(options.field)
doplot = options.doplot
plotants = options.plotants
corr = int(options.corr)
t0 = float(options.t0)
t1 = float(options.t1)
yu0 = float(options.yu0)
yu1 = float(options.yu1)
yl0 = float(options.yl0)
yl1 = float(options.yl1)
mycmap = options.mycmap
mysize = int(options.mysize)
myms = options.myms
pngname = options.pngname


if len(args) != 1:
	print 'Please specify a bandpass table to plot.'
	sys.exit(-1)
else:
	mytab = args[0].rstrip('/')

if pngname == '':
	pngname = 'plot_'+mytab+'_corr'+str(corr)+'_'+doplot+'_field'+str(field)+'.html'
	output_file(pngname)


if doplot not in ['ap','ri']:
	print 'Plot selection must be either ap (amp and phase) or ri (real and imag)'
	sys.exit(-1)


tt = table(mytab,ack=False)
#getting the unique antenna numbers
#getting the unique antenna channels and storing them as list in the ants variable
ants = numpy.unique(tt.getcol('ANTENNA1'))
#getting the field column
fields = numpy.unique(tt.getcol('FIELD_ID'))

#creating color scale for the different antennas
cNorm = colors.Normalize(vmin=0,vmax=len(ants)-1)
mymap = cm = pylab.get_cmap(mycmap)
scalarMap = cmx.ScalarMappable(norm=cNorm,cmap=mymap)


#check if the field specified is found in the fields column
if int(field) not in fields.tolist():
	print 'Field ID '+str(field)+' not found'
	sys.exit(-1)

#If antennas have been specified to be plotted, store their antenna ids into the plotants variable, otherwise, get the entire antennas table from the table
if plotants[0] != -1:
	plotants = plotants.split(',')
	for ant in plotants:
		if int(ant) not in ants:
			plotants.remove(ant)
			print 'Requested antenna ID '+str(ant)+' not found'
	if len(plotants) == 0:
		print 'No valid antennas indices requested'
		sys.exit(-1)
else:
	plotants = ants

#if reference ms is specified, the get the antenna names from there otherwise leave antenna names list empty
if myms != '':
	anttab = table(myms.rstrip('/')+'/ANTENNA')
	antnames = anttab.getcol('NAME')
	anttab.done()
else:
	antnames = ''

#creating the mpl figure for subplots	
ax1 = figure()
ax2 = figure()


xmin = 1e20
xmax = -1e20
ylmin = 1e20
ylmax = -1e20
yumin = 1e20
yumax = -1e20


#for each antenna
for ant in plotants:
	y1col = scalarMap.to_rgba(float(ant))
	y2col = scalarMap.to_rgba(float(ant))

	y1col=np.array(y1col)
	y1col=np.array(y1col*255,dtype=int)
	y1col=y1col.tolist()
	y1col=tuple(y1col)



	y2col=np.array(y2col)
	y2col=np.array(y2col*255,dtype=int)
	y2col=y2col.tolist()
	y2col=tuple(y2col)


	#from the table provided, get the antenna and the field ID columns
	mytaql = 'ANTENNA1=='+str(ant)+' && '
	mytaql+= 'FIELD_ID=='+str(field)


	subtab = tt.query(query=mytaql)
	#get the cparam column from the table
	cparam = subtab.getcol('CPARAM')
	#et the flagged channels column
	flagcol = subtab.getcol('FLAG')

	#shape returns a tuple and store that numbre as the number of channels in the data table
	nchan = cparam.shape[1]
	chans = numpy.arange(0,nchan,dtype='int')

	#masking the flagged channels and storing them into the masked data table.
	#if this is not done, the flagged data will also be plotted
	#if masked, the value is the nullified and not plottted
	masked_data = numpy.ma.array(data=cparam,mask=flagcol)

	#chosing if the complex values are plotted as amplitude and phase or as real and imaginary values
	if doplot == 'ap':
		y1 = numpy.abs(masked_data)[0,:,corr]
		#pdb.set_trace()
		y2 = numpy.angle(masked_data[0,:,corr])
		y2 = numpy.array(y2)
#		y2 = numpy.unwrap(y2)
		ax1.line(chans,y1,color=y1col[:-1],legend="A"+str(ant),line_width=2)
		#ax1.circle(chans,y1,color=y1col[:-1])
		#ax1.legend.click_policy='hide'
		ax2.line(chans,y2,color=y2col[:-1],legend="A"+str(ant),line_width=2)
		
		#ax2.plot(chans,y2,'-',lw=2,alpha=0.4,zorder=100,color=y2col)
	elif doplot == 'ri':
		y1 = numpy.real(masked_data)[0,:,corr]
		y2 = numpy.imag(masked_data)[0,:,corr]
		ax1.line(chans,y1,color=y1col[:-1],legend="A"+str(ant),line_width=2)
		ax1.legend.click_policy='hide'
		#ax1.plot(chans,y1,'-',lw=2,alpha=0.4,zorder=100,color=y1col)
		ax2.line(chans,y2,color=y2col[:-1],legend="A"+str(ant),line_width=2)
		#ax2.plot(chans,y2,'-',lw=2,alpha=0.4,zorder=100,color=y2col)

	#configuring click actions for legends
	ax2.legend.click_policy='hide'
	ax1.legend.click_policy='hide'

	subtab.close()

	dx = 1.0/float(len(ants)-1)
	
	if antnames == '':
		antlabel = str(ant)
	else:
		antlabel = antnames[ant]
	#ax1.text(float(ant)*dx,1.05,antlabel,size='large',horizontalalignment='center',color=y1col,transform=ax1.transAxes,weight='heavy',rotation=90)

	#getting the maximum and minimum number of channels to set  the axes forthe plots
	if numpy.min(chans) < xmin:
		xmin = numpy.min(chans)
	if numpy.max(chans) > xmax:
		xmax = numpy.max(chans)
	if numpy.min(y1) < yumin:
		yumin = numpy.min(y1)
	if numpy.max(y1) > yumax:
		yumax = numpy.max(y1)
	if numpy.min(y2) < ylmin:
		ylmin = numpy.min(y2)
	if numpy.max(y2) > ylmax:
		ylmax = numpy.max(y2)

#loverign the min further and increasing the maximum x these are for the x and y limits for the axes
xmin = xmin-4
xmax = xmax+4
if yumin < 0.0:
	yumin = -1*(1.1*numpy.abs(yumin))
else:
	yumin = yumin*0.9
yumax = yumax*1.1
if ylmin < 0.0:
	ylmin = -1*(1.1*numpy.abs(ylmin))
else:
	ylmin = ylmin*0.9
ylmax = ylmax*1.1

if t0 != -1:
	xmin = float(t0)
if t1 != -1:
	xmax = float(t1)
if yl0 != -1:
	ylmin = yl0
if yl1 != -1:
	ylmax = yl1
if yu0 != -1:
	yumin = yu0
if yu1 != -1:
	yumax = yu1


ax1.x_range=Range1d(xmin,xmax)
ax2.x_range=Range1d(xmin,xmax)
ax1.y_range=Range1d(yumin,yumax)
ax2.y_range=Range1d(ylmin,ylmax)

#setting the axes labels depending on what mode the plots are  i.e real imaginary or amplitude and phase
if doplot == 'ap':
	ax1.yaxis.axis_label='Amplitude'
	ax2.yaxis.axis_label='Phase [rad]'
elif doplot == 'ri':
	ax1.yaxis.axis_label='Real'
	ax2.yaxis.axis_label='Imaginary'

ax1.xaxis.axis_label='Channel'
ax2.xaxis.axis_label='Channel'


'''fig.suptitle(pngname)
set_fontsize(fig,mysize)
fig.savefig(pngname,bbox_inches='tight')'''
figures=row(ax1,ax2)
show(figures)

print 'Rendered: '+pngname
