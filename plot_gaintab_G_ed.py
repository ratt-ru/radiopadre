#!/usr/bin/env python
'''
Run script with desired B tables
Requirement: bokeh
'''

from pyrap.tables import table
from optparse import OptionParser
import matplotlib.colors as colors 
import matplotlib.cm as cmx 
import glob

import pylab	
import sys


from bokeh.plotting import figure
from bokeh.io import output_file, show
from bokeh.layouts import row, column, gridplot
from bokeh.models import Range1d, HoverTool, ColumnDataSource
import numpy as np


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
	print 'Please specify a gain table to plot.'
	sys.exit(-1)
else:
	#getting the name of the gain table specified
	mytab = args[0].rstrip('/')


if pngname == '':
	pngname = 'plot_'+mytab+'_corr'+str(corr)+'_'+doplot+'_field'+str(field)+'.html'
	output_file(pngname)
else:
	output_file(pngname)


#by default is ap: amplitude and phase
if doplot not in ['ap','ri']:
	print 'Plot selection must be either ap (amp and phase) or ri (real and imag)'
	sys.exit(-1)


#opening the selected table
tt = table(mytab,ack=False)

ants = np.unique(tt.getcol('ANTENNA1'))
fields = np.unique(tt.getcol('FIELD_ID'))
flags = tt.getcol('FLAG')

#building the colormap fo the plot
cNorm = colors.Normalize(vmin=0,vmax=len(ants)-1)
mymap = cm = pylab.get_cmap(mycmap)
scalarMap = cmx.ScalarMappable(norm=cNorm,cmap=mymap)


if int(field) not in fields.tolist():
	print 'Field ID '+str(field)+' not found'
	sys.exit(-1)


if plotants[0] != -1:
	#creating a list for the antennas to be plotted
	plotants = plotants.split(',')

	for ant in plotants:
		if int(ant) not in ants:
			plotants.remove(ant)
			print 'Requested antenna ID '+str(ant)+' not found'
	if len(plotants) == 0:
		print 'No valid antennas have been requested'
		sys.exit(-1)
	else:
		plotants = np.array(plotants,dtype=int)
else:
	plotants = ants

if myms != '':
	anttab = table(myms.rstrip('/')+'/ANTENNA')
	antnames = anttab.getcol('NAME')
	anttab.done()
else:
	antnames = ''



TOOLS = dict(tools= 'box_select, box_zoom, reset, pan, save, wheel_zoom')
ax1=figure(plot_width=800, plot_height=800, **TOOLS)

#linking plots ax1 and ax2 via the x_axes because of similarities in range
#y axes not linkable due to differences in magnitude
ax2=figure(plot_width=800, plot_height=800, x_range=ax1.x_range, **TOOLS)


xmin = 1e20
xmax = -1e20
ylmin = 1e20
ylmax = -1e20
yumin = 1e20
yumax = -1e20

#Setting tooltip data for ax1 and ax2
hover=HoverTool(tooltips=[("(time,y1)","($x,$y)")],mode='mouse')
hover.point_policy='snap_to_data'
hover2=HoverTool(tooltips=[("(time,y2)","($x,$y)")],mode='mouse')
hover2.point_policy='snap_to_data'


for ant in plotants:
	
	y1col = scalarMap.to_rgba(float(ant))
	y2col = scalarMap.to_rgba(float(ant))

	#denormalize y1col an 2col rgba from 0-1 and convert to rgb (0-255)
	
	y1col=np.array(y1col)
	y1col=np.array(y1col*255,dtype=int)
	y1col=y1col.tolist()
	y1col=tuple(y1col)[:-1]



	y2col=np.array(y2col)
	y2col=np.array(y2col*255,dtype=int)
	y2col=y2col.tolist()
	y2col=tuple(y2col)[:-1]


	mytaql = 'ANTENNA1=='+str(ant)
	
	subtab = tt.query(query=mytaql)
	cparam = subtab.getcol('CPARAM')
	flagcol = subtab.getcol('FLAG')
	times = subtab.getcol('TIME')

	#setting time relative to initial time
	times = times - times[0]
	#creating a masked array to prevent invalid values from being computed. IF mask is true, then the element is masked, an dthus won't be used in the calculation
	#removing flagged data from cparams
	masked_data = np.ma.array(data=cparam,mask=flagcol)

	

	if doplot == 'ap':
		
		y1 = np.abs(masked_data)[:,0,corr]
		#y1 = np.array(y1)
	
		y2 = np.angle(masked_data)
		y2 = np.array(y2[:,:,corr])
		#remove phase limit from -pi to pi
		y2 = np.unwrap(y2[:,0])
		y2 = np.rad2deg(y2)
		
		source=ColumnDataSource(data=dict(x=times, y1=y1, y2=y2))
		ax1.circle('x','y1',size=8,alpha=1, color=y1col,source=source,legend="A "+str(ant), nonselection_color='#7D7D7D',nonselection_fill_alpha=0.3)
		ax2.circle('x','y2',size=8,alpha=1, color=y2col, legend='A '+str(ant),source=source,  nonselection_color='#7D7D7D',nonselection_fill_alpha=0.3)

		ax1.yaxis.axis_label=ax1_ylabel='Amplitude'
		ax2.yaxis.axis_label=ax2_ylabel='Unwrapped phase [Deg]' 
	elif doplot == 'ri':
		y1 = np.real(masked_data)[:,0,corr]
		y2 = np.imag(masked_data)[:,0,corr]
		
		source=ColumnDataSource(data=dict(x=times, y1=y1, y2=y2))
		ax1.circle('x','y1',size=8,alpha=1,line_dash='dashed', color=y1col,source=source,legend="A "+str(ant), nonselection_color='#7D7D7D',nonselection_fill_alpha=0.3)
		ax2.line('x','y2',color=y2col,line_dash='dashed', alpha=1, line_width=2,legend="A "+str(ant), source=source, nonselection_color='#7D7D7D',nonselection_line_alpha=0.3)
		ax2.circle('x','y2',size=8,alpha=1, color=y2col,source=source,legend="A "+str(ant), nonselection_color='#7D7D7D',nonselection_fill_alpha=0.3)
		ax1.yaxis.axis_label=ax1_ylabel='Real'
		ax2.yaxis.axis_label=ax2_ylabel='Imaginary'
	

	subtab.close()

	
	if antnames == '':
		antlabel = str(ant)
	else:
		antlabel = antnames[ant]

	if np.min(times) < xmin:
		xmin = np.min(times)
	if np.max(times) > xmax:
		xmax = np.max(times)
	if np.min(y1) < yumin:
		yumin = np.min(y1)
	if np.max(y1) > yumax:
		yumax = np.max(y1)
	if np.min(y2) < ylmin:
		ylmin = np.min(y2)
	if np.max(y2) > ylmax:
		ylmax = np.max(y2)

#adding tooltips to the figure
ax1.add_tools(hover)
ax2.add_tools(hover2)
ax1.legend.click_policy=ax2.legend.click_policy='hide'
#setting the axis limits for scaliing
xmin = xmin-400
xmax = xmax+400

if yumin < 0.0:
	yumin = -1*(1.1*np.abs(yumin))
else:
	yumin = yumin*0.9
yumax = yumax*1.1
if ylmin < 0.0:
	ylmin = -1*(1.1*np.abs(ylmin))
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


#aconfiguring only y_range because xrange for ax2 is dependent on ax1
ax1.y_range=Range1d(yumin,yumax)
ax2.y_range=Range1d(ylmin,ylmax)


ax1.xaxis.axis_label = ax1_xlabel='Time [s]'
ax2.xaxis.axis_label = ax2_xlabel='Time [s]'

#configuring both figure titles (font size and alignment)
ax1.title.text = ax1_ylabel + ' vs ' + ax1_xlabel
ax1.title.align='center'
ax1.title.text_font_size='25px'
ax2.title.text = ax2_ylabel + ' vs ' + ax2_xlabel
ax2.title.align='center'
ax2.title.text_font_size='25px'


#setting the layout of the figures
figures=gridplot([[ax1,ax2]])
show(figures)
print 'Rendered: '+pngname
