
#
# Hubblemon - Yet another general purpose system monitor
#
# Copyright 2015 NAVER Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
from chart.chart_data import chart_data
from chart.chart_data import chart_item
import common.settings

              
class basic_loader:
	def __init__(self, handle, filter, title=''):
		self.filter = filter

		self.handle = handle

		self.title = title
		self.data = {}

		self.ts_start = None
		self.ts_end = None

		self.renderer = {}
		flot_line = flot_line_renderer()
		self.renderer['default'] = flot_line
		self.renderer['line'] = flot_line
		self.renderer['title'] = title_renderer()
		self.renderer['stack'] = flot_stack_renderer()

	def count(self, name):
		if self.handle is None:
			return 0

		sum = 0

		if name in self.data:
			chart = self.data[name]
			item = chart.items[0] # should be 1 metric 

			for ts_value in item.data:
				if ts_value == None:
					continue

				sum += ts_value[1]
		return sum

	def avg(self, name):
		if self.handle is None:
			return 0

		sum = 0
		avg = 0

		if name in self.data:
			chart = self.data[name]
			item = chart.items[0] # should be 1 metric 

			for ts_value in item.data:
				if ts_value == None:
					continue

				sum += ts_value[1]

			avg = sum / len(item.data)

		return avg

	def max(self, name):
		if self.handle is None:
			return 0

		max = 0

		if name in self.data:
			chart = self.data[name]
			item = chart.items[0] # should be 1 metric 

			for ts_value in item.data:
				if ts_value == None:
					continue

				if ts_value[1] > max:
					max = ts_value[1]
		return max

	def min(self, name):
		if self.handle is None:
			return 0

		min = sys.maxsize

		if name in self.data:
			chart = self.data[name]
			item = chart.items[0] # should be 1 metric 

			for ts_value in item.data:
				if ts_value == None:
					continue

				if ts_value[1] < min:
					min = ts_value[1]
		return min

	def parse(self, ts_start, ts_end):
		self.ts_start = ts_start
		self.ts_end = ts_end

		if self.handle is None:
			return

		chart_data_list = self.load(ts_start, ts_end)

		self.data = {}
		for chart_data in chart_data_list:
			self.data[chart_data.title] = chart_data

	def make_chart(self, titles, tmap, items, ts_start, ts_step):
		if isinstance(titles, str):
			idx = tmap[titles]
			data = []

			ts_count = 0
			for item in items:
				if ts_start is None:
					ts = item[0]
				else:
					ts = ts_start + ts_count * ts_step
					ts_count += 1

				if item[idx] == None:
					data.append(None)
					continue

				data.append([ts, item[idx]])

			return [(titles, data)]

		elif isinstance(titles, tuple):
			title = ''

			for func in titles:
				if not hasattr(func, '__call__'):
					title = func

			data = []
			ts_count = 0
			input = { 'prev':{} }

			for item in items:
				if ts_start is None:
					ts = item[0]
				else:
					ts = ts_start + ts_count * ts_step
					ts_count += 1

				for name, idx in tmap.items():
					input[name] = item[idx]

				for func in titles: # only last function result is saved
					if hasattr(func, '__call__'):
						try:
							output = [ts, func(input)]
						except:
							output = None

				prev = input['prev']
				for k, v in input.items():
					if k == 'prev':
						continue

					if k not in prev:
						prev[k] = []
					
					prev[k].append(v)

				data.append(output)

			return [(title, data)]

		elif isinstance(titles, list):
			ret = []
			for title in titles:
				if title.startswith('#'):
					continue

				ret += self.make_chart(title, tmap, items, ts_start, ts_step)
		
			return ret

		return []


	def load(self, ts_start, ts_end):
		self.ts_start = ts_start
		self.ts_end = ts_end

		if self.handle is None:
			print ('invalid handle')
			return []

		ret = self.handle.read(ts_start, ts_end)
		# default(rrd) type ((ts_start, ts_end, step), (metric1, metric2, metric3), [(0, 0, 0), (1, 1, 1)....])
		# rrd type ('#rrd', (ts_start, ts_end, step), (metric1, metric2, metric3), [(0, 0, 0), (1, 1, 1)....])
		# tsdb type ('#timestamp', (metric1, metric2, metric3), [(ts, 0, 0, 0), (ts, 1, 1, 1)....])
		tmap = {}

		if isinstance(ret[0], str):
			if ret[0] == '#timestamp':
				ts_start = None
				ts_step = None

				names = ret[1]
				items = ret[2]
			else:
				ts_start = ret[1][0] * 1000
				ts_step = ret[1][2] * 1000
				
				names = ret[2]
				items = ret[3]

			for i in range(0, len(names)):
				tmap[names[i]] = i+1 # skip 1 for tag

		else:	# implicit rrd style
			ts_start = ret[0][0] * 1000
			ts_step = ret[0][2] * 1000
			
			names = ret[1]
			items = ret[2]

			for i in range(0, len(names)):
				tmap[names[i]] = i

		# for debug
		#print(tmap)
		#print(names)
		#print(items)
			
		# loader title
		chart_data_list = []
		
		if self.title != '':
			title_chart = chart_data()
			title_chart.title = self.title
			title_chart.renderer = self.renderer['title']
			chart_data_list.append(title_chart)

		
		if self.filter == None: 	# select all
			self.filter = names

		#print(self.filter)
		for titles in self.filter: # for each chart
			new_chart = chart_data()

			tmp_list = self.make_chart(titles, tmap, items, ts_start, ts_step)
			for tmp in tmp_list:
				new_chart.push_data(tmp[0], tmp[1])
				
#			if(titles[0]=='#stack'):
			
#				stack_data = tmp_list[0][1]
#				for tmp in tmp_list[1:]:					
#					for z in range(len(stack_data)):
#						if z > len(tmp[1])-1:
#							break
#						if stack_data[z]!=None and tmp[1][z]!=None:
#							if (stack_data[z][0] == tmp[1][z][0]):
#								stack_data[z][1] += tmp[1][z][1]
#						else:
#							print("stack x-axis not good----------------")
#							continue
#				print('len////////////')
#				print(len(stack_data))
#				for i in range(len(stack_data)):
#					if stack_data[i]!=None:
#						print('from %d' %i)
#						break
#				for j in range(i, len(stack_data)):
#					if stack_data[j]==None:
#						print('to %d' %j)
#						break
				
#				new_chart.push_data('stack', stack_data)	
			renderer_name = 'default'
			if isinstance(titles, list) and titles[0].startswith('#'): # renderer
				renderer_name = titles[0][1:]
				
			if renderer_name in self.renderer:
				new_chart.renderer = self.renderer[renderer_name]

			chart_data_list.append(new_chart)	
		return chart_data_list


class title_renderer:
	def render(self, chart_data):
		title_template = self.get_title_template()
		return title_template % chart_data.title

	def get_title_template(self):
		title_template = '''
			<div class="chart-seperator" style="clear:both">
				<p>%s</p>
			</div>
		'''

		return title_template



class flot_line_renderer:
	idx = 1

	def render(self, chart_data):
		chart_data.sampling(common.settings.chart_resolution)

		# adjust timezone if needed
		mode = ''
		if chart_data.mode == 'time':
			mode = 'xaxis: { mode: "time" }, yaxis: { tickFormatter: tickFunc, min: 0 }, lines: { fillOpacity:1.0, show: true, lineWidth:1 },'
			chart_data.adjust_timezone()

		# convert python array to js array
		raw_data = ''
		if len(chart_data.items) == 1: # one item
			raw_data = chart_data.items[0].data.__repr__().replace('None', 'null')
		else: # multi item (display label)
			for item in chart_data.items:
				tmp = item.data.__repr__().replace('None', 'null')
				if len(chart_data.items) > 7:
					raw_data += '%s,' % tmp
				else:
					raw_data += '{ label: "%s", data: %s },' % (item.title, tmp)

		idx = flot_line_renderer.idx + id(chart_data) # to get unique idx
		flot_line_renderer.idx += 1

		#print (raw_data)
		js_template = self.get_js_template()
		return  js_template % ('[ %s ]' % raw_data, idx, mode, chart_data.title, idx)

		
	def get_js_template(self):
		js_template = '''
			<script type="text/javascript">

			$(function() {
				tickFunc = function(val, axis) {
					if (val > 1000000000 && (val %% 1000000000) == 0) {
						return val/1000000000 + "G";
					}
					else if (val > 1000000 && (val %% 1000000) == 0) {
						return val/1000000 + "M";
					}
					else if (val < 1) {
						return Math.round(val*1000)/1000
					}

					return val;
				};

				var data_list = %s
				$.plot("#placeholder_%s", data_list, {
					%s
				});
			});
			</script>

			<div>
			<div class="chart-container">
				<div class="chart-title">%s</div>
				<div id="placeholder_%s" class="chart-placeholder" style="float:left"></div>
			</div>
			</div>
		'''

		return js_template


class flot_stack_renderer:
	idx = 1
	tmp_stack=[]
	def render(self, chart_data):
		chart_data.sampling(common.settings.chart_resolution)

		# adjust timezone if needed
		mode = ''
		if chart_data.mode == 'time':
			mode = 'xaxis: { mode: "time" }, yaxis: { tickFormatter: tickFunc, min: 0 }, lines: { fillOpacity:1.0, show: true, lineWidth:1 },'
			chart_data.adjust_timezone()

		for y in range(len(chart_data.items)):
			if y==0:			
				tmp_stack=chart_data.items[0].data
			else:
				for z in range(len(tmp_stack)):
					if z > len(chart_data.items[y].data)-1:
						break
					if tmp_stack[z]!=None and chart_data.items[y].data[z]!=None: 
						if (tmp_stack[z][0] == chart_data.items[y].data[z][0]):
							tmp_stack[z][1]+=chart_data.items[y].data[z][1]
					else:
						print("stack x-axis not good----------------")
						continue
		
			
		item_stack=chart_item('stack', tmp_stack)
		chart_data.items.append(item_stack)
		
		# convert python array to js array
		raw_data = ''
	
		if len(chart_data.items) == 1: # one item
			raw_data = chart_data.items[0].data.__repr__().replace('None', 'null')
		else: # multi item (display label)

			for item in chart_data.items:
				tmp = item.data.__repr__().replace('None', 'null')
				print(item.title)	
				if len(chart_data.items) > 7:
					raw_data += '%s,' % tmp
				else:					
					raw_data += '{ label: "%s", data: %s },' % (item.title, tmp)
	
		 	
	#	tmp = tmp_stack.__repr__().replace('None', 'null')
	#	raw_data += '{ label: "stack", data: %s },' %(tmp)
	#
		idx = flot_stack_renderer.idx + id(chart_data) # to get unique idx
		flot_stack_renderer.idx += 1

		#print (raw_data)
		js_template = self.get_js_template()
		print(idx)
		print(mode)
		print(chart_data.title)
		return  js_template % ('[ %s ]' % raw_data, idx, mode, chart_data.title, idx)

		
	def get_js_template(self):
		js_template = '''
			<script type="text/javascript">

			$(function() {
				tickFunc = function(val, axis) {
					if (val > 1000000000 && (val %% 1000000000) == 0) {
						return val/1000000000 + "G";
					}
					else if (val > 1000000 && (val %% 1000000) == 0) {
						return val/1000000 + "M";
					}
					else if (val < 1) {
						return Math.round(val*1000)/1000
					}

					return val;
				};

				var data_list = %s
				$.plot("#placeholder_%s", data_list, {
					%s
				});
			});
			</script>

			<div>
			<div class="chart-container">
				<div class="chart-title">%s</div>
				<div id="placeholder_%s" class="chart-placeholder" style="float:left"></div>
			</div>
			</div>
		'''

		return js_template




