import pdb
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
from bokeh.models import Range1d, HoverTool, ColumnDataSource, LinearAxis, FixedTicker
from bokeh.io import output_file, show
from bokeh.layouts import row, column, gridplot

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

spw_table=freqs= ''

if len(args) != 1:
	print 'Please specify a bandpass table to plot.'
	sys.exit(-1)
else:
	mytab = args[0].rstrip('/')
	

if '.B0' in mytab:
	spw_table = str(mytab) +'/SPECTRAL_WINDOW'

if '.K0' in mytab:
	field=1

if pngname == '':
	pngname = 'plot_'+mytab+'_corr'+str(corr)+'_'+doplot+'_field'+str(field)+'.html'
	output_file(pngname)
else:
	#name provided and stored in png format
	output_file(pngname)

if doplot not in ['ap','ri']:
	print 'Plot selection must be either ap (amp and phase) or ri (real and imag)'
	sys.exit(-1)


tt = table(mytab,ack=False)
antenna1=tt.getcol('ANTENNA1')
ants = np.unique(antenna1)
fields = np.unique(tt.getcol('FIELD_ID'))
flags = tt.getcol('FLAG')

#get channel frequencies from spectral window subtable if plotting bandpass tables

if spw_table:
	spw=table(spw_table, ack=False)
	freqs = spw.getcol('CHAN_FREQ')[0]
	spw.close()

#colors
#getting colormaps for the graph
cNorm = colors.Normalize(vmin=0,vmax=len(ants)-1)
mymap = cm = pylab.get_cmap(mycmap)
scalarMap = cmx.ScalarMappable(norm=cNorm,cmap=mymap)

def color_denormalize(ycol):
	'''
		converting rgb values from 0 to 255

	'''
	ycol=np.array(ycol)
	ycol=np.array(ycol*255,dtype=int)
	ycol=ycol.tolist()
	ycol=tuple(ycol)[:-1]
	
	return ycol

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

#plot tools config and and the x_axes because fo similarities in range
TOOLS = dict(tools= 'box_select, box_zoom, reset, pan, save, wheel_zoom')
ax1=figure(plot_width=600, plot_height=600, **TOOLS)
ax2=figure(plot_width=600, plot_height=600, x_range=ax1.x_range, **TOOLS)

if freqs != '':
	ax1.extra_x_ranges={"foo": Range1d(start=freqs[0], end=freqs[-1])}
	linaxis = LinearAxis(x_range_name="foo", axis_label='Frequencies',  major_label_orientation='vertical')
	ax1.add_layout(linaxis, 'above')

#setting min and max ranges for x and y
xmin = 1e20
xmax = -1e20
ylmin = 1e20
ylmax = -1e20
yumin = 1e20
yumax = -1e20



def plot_titles(fig):
	'''
		fig: figure object
	'''
	fig.title.align='center'
	fig.title.text_font_size='25px'
	fig.legend.click_policy='hide'

def plot_G(x_param,y_param):
	'''
		x: x_axis parameter
		y: y axis parameter for cparams field
	'''
	global xmin, xmax,ylmin,ylmax,yumin,yumax
	if doplot == 'ap':
		y1 = np.abs(y_param)[:,0,corr]	
		y2 = np.angle(y_param)
		y2 = np.array(y2[:,:,corr])
		y2 = np.unwrap(y2[:,0])
		y2 = np.rad2deg(y2)
		pdb.set_trace()
		source=ColumnDataSource(data=dict(x=x_param, y1=y1, y2=y2))
		ax1.circle('x','y1',size=8,alpha=1, color=y1col,source=source,legend="A "+str(ant), nonselection_color='#7D7D7D',nonselection_fill_alpha=0.3)
		ax2.circle('x','y2',size=8,alpha=1, color=y2col, legend='A '+str(ant),source=source,  nonselection_color='#7D7D7D',nonselection_fill_alpha=0.3)
		ax1.yaxis.axis_label=ax1_ylabel='Amplitude'
		ax2.yaxis.axis_label=ax2_ylabel='Unwrapped phase [Deg]'
	elif doplot == 'ri':
		y1 = np.real(y_param)[:,0,corr]
		y2 = np.imag(y_param)[:,0,corr]
		source=ColumnDataSource(data=dict(x=x_param, y1=y1, y2=y2))
		ax1.circle('x','y1',size=8,alpha=1,line_dash='dashed', color=y1col,source=source,legend="A "+str(ant), nonselection_color='#7D7D7D',nonselection_fill_alpha=0.3)
		ax2.circle('x','y2',size=8,alpha=1, color=y2col,source=source,legend="A "+str(ant), nonselection_color='#7D7D7D',nonselection_fill_alpha=0.3)
		ax1.yaxis.axis_label=ax1_ylabel='Real'
		ax2.yaxis.axis_label=ax2_ylabel='Imaginary'

	ax1.xaxis.axis_label = ax2.xaxis.axis_label=ax1_xlabel=ax2_xlabel='Time [s]'
	ax1.title.text = ax1_ylabel + ' vs ' + ax1_xlabel
	ax2.title.text = ax2_ylabel + ' vs ' + ax2_xlabel


	dx = 1.0/float(len(ants)-1)
	if antnames == '':
		antlabel = str(ant)
	else:
		antlabel = antnames[ant]
	
	if np.min(x_param) < xmin:
		xmin = np.min(x_param)
	if np.max(x_param) > xmax:
		xmax = np.max(x_param)
	if np.min(y1) < yumin:
		yumin = np.min(y1)
	if np.max(y1) > yumax:
		yumax = np.max(y1)
	if np.min(y2) < ylmin:
		ylmin = np.min(y2)
	if np.max(y2) > ylmax:
		ylmax = np.max(y2)


def plot_B(x_param,y_param):
	
	global xmin, xmax,ylmin,ylmax,yumin,yumax
	if doplot == 'ap':
		#for all the channels
		y1 = np.abs(y_param)[0,:,corr]
		y2 = np.angle(y_param[0,:,corr])
		y2 = np.array(y2)
		y2 = np.unwrap(y2)
		y2 = np.rad2deg(y2)
		
		source=ColumnDataSource(data=dict(x=x_param,y1=y1,y2=y2))
		ax1.circle('x','y1',color=y1col,legend="A"+str(ant),size=8, source=source, nonselection_color='#7D7D7D',nonselection_line_alpha=0.3)
		ax2.circle('x','y2',color=y2col,legend="A"+str(ant),size=8, source=source, nonselection_color='#7D7D7D',nonselection_line_alpha=0.3)
		ax1.yaxis.axis_label=ax1_ylabel='Amplitude'
		ax2.yaxis.axis_label=ax2_ylabel='Phase [Deg]'
	elif doplot == 'ri':
		y1 = np.real(y_param)[0,:,corr]
		y2 = np.imag(y_param)[0,:,corr]
		
		source=ColumnDataSource(data=dict(x=x_param,y1=y1,y2=y2))
		ax1.circle('x','y1',color=y1col,legend="A"+str(ant),size=8, source=source, nonselection_color='#7D7D7D',nonselection_line_alpha=0.3)
		ax2.circle('x','y2',color=y2col,legend="A"+str(ant),lsize=8, source=source, nonselection_color='#7D7D7D',nonselection_line_alpha=0.3)
		
		ax1.yaxis.axis_label=ax1_ylabel='Real'
		ax2.yaxis.axis_label=ax2_ylabel='Imaginary'

	ax1.xaxis.axis_label = ax2.xaxis.axis_label=ax1_xlabel=ax2_xlabel='Channel'
	ax1.title.text = ax1_ylabel + ' vs ' + ax1_xlabel
	ax2.title.text = ax2_ylabel + ' vs ' + ax2_xlabel

	#dx = 1.0/float(len(ants)-1)
	#unnecessary?
	
	if antnames == '':
		antlabel = str(ant)
	else:
		antlabel = antnames[ant]
	#ax1.text(float(ant)*dx,1.05,antlabel,size='large',horizontalalignment='center',color=y1col,transform=ax1.transAxes,weight='heavy',rotation=90)

	#getting the maximum and minimum number of channels to set  the axes forthe plots
	if np.min(x_param) < xmin:
		xmin = np.min(x_param)
	if np.max(x_param) > xmax:
		xmax = np.max(x_param)
	if np.min(y1) < yumin:
		yumin = np.min(y1)
	if np.max(y1) > yumax:
		yumax = np.max(y1)
	if np.min(y2) < ylmin:
		ylmin = np.min(y2)
	if np.max(y2) > ylmax:
		ylmax = np.max(y2)	


def plot_K(x_param, y_param):
	global xmin, xmax,ylmin,ylmax,yumin,yumax
	if doplot == 'ap':
		#for all the channels
		#pdb.set_trace()
		y1 = y_param[:,0,corr]

		#pdb.set_trace()
		#done to convert masked array to array
		y1=np.array(y1)
		y2=y_param[:,0,1]
		source=ColumnDataSource(data=dict(x=x_param,y1=y1,y2=y2))
		ax1.circle('x','y1',color=y1col,legend="A"+str(ant),size=8, source=source, nonselection_color='#7D7D7D',nonselection_line_alpha=0.3)
		
		ax2.circle('x','y2',color=y2col,legend="A"+str(ant),size=8, source=source,  nonselection_color='#7D7D7D',nonselection_line_alpha=0.3)
		
		ax1.yaxis.axis_label=ax1_ylabel ='Delay [Correlation 0]'
		ax2.yaxis.axis_label=ax2_ylabel ='Delay [Correlation 1]'
		ax1.xaxis.axis_label=ax2.xaxis.axis_label= ax1_xlabel= ax1_xlabel='Antenna1'


		
	elif doplot == 'ri':
		print "No complex values to plot"

	
	if antnames == '':
		antlabel = str(ant)
	else:
		antlabel = antnames[ant]

	ax1.xaxis.axis_label = ax2.xaxis.axis_label=ax1_xlabel=ax2_xlabel='Channel'
	ax1.title.text = ax1_ylabel + ' vs ' + ax1_xlabel
	ax2.title.text = ax2_ylabel + ' vs ' + ax2_xlabel
	#getting the maximum and minimum number of channels to set  the axes forthe plots
	if np.min(ant) < xmin:
		xmin = np.min(x_param)
	if np.max(x_param) > xmax:
		xmax = np.max(x_param)
	if np.min(y1) < yumin:
		yumin = np.min(y1)
	if np.max(y1) > yumax:
		yumax = np.max(y1)
	if np.min(y2) < ylmin:
		ylmin = np.min(y2)
	if np.max(y2) > ylmax:
		ylmax = np.max(y2)


for ant in plotants:
	#color maps for the two plots
	y1col = scalarMap.to_rgba(float(ant))
	y2col = scalarMap.to_rgba(float(ant))

	y1col = color_denormalize(y1col)
	y2col = color_denormalize(y2col)

	mytaql = 'ANTENNA1=='+str(ant)+' && '
	mytaql+= 'FIELD_ID=='+str(field)

	subtab = tt.query(query=mytaql)
	flagcol = subtab.getcol('FLAG')
	times = subtab.getcol('TIME')
	times=times-times[0]

	if '.GO' in mytab or '.BO' in mytab:
		cparam = subtab.getcol('CPARAM')
		nchan = cparam.shape[1]
		masked_data = np.ma.array(data=cparam,mask=flagcol)
		chans = numpy.arange(0,nchan,dtype='int')

	else:
		fparam = subtab.getcol('FPARAM')
	
	

	#check the table that was provided
	if '.G0' in mytab:
		plot_G(times, masked_data)
		xmin = xmin-400
		xmax = xmax+400
		hover=HoverTool(tooltips=[("(times,y1)","($x,$y)")],mode='mouse')
		hover2=HoverTool(tooltips=[("(times,y2)","($x,$y)")],mode='mouse')
		hover.point_policy=hover2.point_policy='snap_to_data'

	elif '.B0' in mytab:
		plot_B(chans,cparam)
		xmin = xmin-400
		xmax = xmax+400
		hover=HoverTool(tooltips=[("(chans,y1)","($x,$y)")],mode='mouse')
		hover2=HoverTool(tooltips=[("(chans,y2)","($x,$y)")],mode='mouse')
		hover.point_policy=hover2.point_policy='snap_to_data'
	
	elif '.K0' in mytab:
		ax2.y_range=ax1.y_range
		plot_K(antenna1[antenna1==ant],fparam)
		xmin = xmin-400
		xmax = xmax+400
		hover=HoverTool(tooltips=[("(antenna1,y1)","($x,$y)")],mode='mouse')
		hover2=HoverTool(tooltips=[("(antenna1,y2)","($x,$y)")],mode='mouse')
		hover.point_policy=hover2.point_policy='snap_to_data'	

	subtab.close()

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

ax1.y_range=Range1d(yumin,yumax)
ax2.y_range=Range1d(ylmin,ylmax)
ax1.add_tools(hover)
ax2.add_tools(hover2)

plot_titles(ax1)
plot_titles(ax2)

figures=gridplot([[ax1,ax2]])
show(figures)