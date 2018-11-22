from django.conf.urls import url
from django.shortcuts import render, HttpResponse, redirect
from django.utils.safestring import mark_safe
from django.shortcuts import reverse
from stark.static.page import Page
from django import forms
from django.db.models import Q
import copy


class ListView:

    def __init__(self, config_obj, request, data_list):
        self.config_obj = config_obj
        self.request = request
        self.data_list = data_list

    def create_head(self):
        # 表头的建立
        heads_list = []
        for field_or_func in self.config_obj.new_list_display():
            if callable(field_or_func):
                head = field_or_func(self.config_obj, is_head=True)
            else:
                if field_or_func != "__str__":
                    field_obj = self.config_obj.model._meta.get_field(field_or_func)
                    head = field_obj.verbose_name
                else:
                    head = self.config_obj.model._meta.model_name
            heads_list.append(head)
        return heads_list

    def create_body(self):
        # 表内容content_list=[[数据1],[数据2],[数据3]....]
        obj_list = []
        for data_obj in self.data_list:
            content_list = []
            for field_or_func in self.config_obj.new_list_display():
                if callable(field_or_func):
                    content = field_or_func(self.config_obj, data_obj)
                else:
                    try:
                        from django.db.models.fields.related import ManyToManyField
                        field_obj = data_obj._meta.get_field(field_or_func)
                        if isinstance(field_obj, ManyToManyField):
                            contents_list = getattr(data_obj, field_or_func).all()
                            content = '||'.join([str(item) for item in contents_list])
                        else:
                            content = getattr(data_obj, field_or_func)
                            if field_or_func in self.config_obj.list_display_links:
                                url = self.config_obj.get_change_url(data_obj)
                                content = mark_safe(f'<a href="{url}">{content}</a>')
                    except:
                        content = getattr(data_obj, field_or_func)
                content_list.append(content)

            obj_list.append(content_list)
        return obj_list

    def actions_list(self):
        actions_list = []
        action_info = []
        if self.config_obj.actions:
            actions_list.extend(self.config_obj.actions)
        actions_list.append(self.config_obj.batch_delete)
        for action in actions_list:
            action_info.append({
                "desc": action.short_description,
                "action": action.__name__
            })
        return action_info

    # filter相关方法
    def filter_field_links(self):
        filter_links = {}

        for field in self.config_obj.list_filter:
            # 从get请求中得到需要的filter参数
            params = copy.deepcopy(self.request.GET)
            choice_field_pk = self.request.GET.get(field, 0)
            # 通过多对多或者一对多的字段得到对应的模型表
            field_obj = self.config_obj.model._meta.get_field(field)
            rel_model = field_obj.rel.to

            # 得到模型表中的所有数据
            ret_model_queryset = rel_model.objects.all()
            tem = []
            for obj in ret_model_queryset:
                # 将对应的对象pk值添加到字典中，以当前model表的字段为键
                params[field] = obj.pk
                if obj.pk == int(choice_field_pk):
                    link = f"<a style='color:red' href='?{params.urlencode()}'>{obj}</a>"
                else:
                    link = f"<a href='?{params.urlencode()}'>{obj}</a>"
                tem.append(link)
            filter_links[field] = tem
        return filter_links


class ModelStark(object):
    """
    默认配置类
    """
    # print(self)#<app01.stark.PublishConfig object at 0x000001531BBC6DD8>
    # print(self.model)#<class 'app01.models.Publish'>
    list_display = ['__str__']
    list_display_links = []
    search_fields = []
    actions = []
    list_filter = []

    def __init__(self, model):
        self.model = model  # 当前模型表
        self.model_name = self.model._meta.model_name  # 当前模型表名
        self.app_label = self.model._meta.app_label  # 当前模型表所属app名

    # 反向解析当前查看表的增删改查的url
    def get_check_url(self):
        url_name = "%s_%s_check" % (self.app_label, self.model_name)
        _url = reverse(url_name)
        return _url

    def get_add_url(self):
        url_name = "%s_%s_add" % (self.app_label, self.model_name)
        _url = reverse(url_name)
        return _url

    def get_change_url(self, obj):
        url_name = "%s_%s_change" % (self.app_label, self.model_name)
        _url = reverse(url_name, args=(obj.pk,))
        return _url

    def get_del_url(self, obj):
        url_name = "%s_%s_delete" % (self.app_label, self.model_name)
        _url = reverse(url_name, args=(obj.pk,))
        return _url

    def edit(self, data_obj=None, is_head=False):
        if is_head:
            return "编辑"
        else:
            return mark_safe(f'<a href={self.get_change_url(data_obj)}><button type="button" class="btn btn-info">编辑</button></a>')

    def delete(self, data_obj=None, is_head=False):
        if is_head:
            return "操作"
        else:
            return mark_safe(f'<a class="delete-link" href="javascript:void(0)" url="{self.get_del_url(data_obj)}">'
                             f'<button type="button" data-toggle="modal" data-target="#myModal"class="btn btn-warning  btn-delete">'
                             f'删除</button></a>')

    def checkbox(self, data_obj=None, is_head=False):
        if is_head:
            return "选择"
        else:
            return mark_safe(f"<input type='checkbox' name='checkbox_pk' value={data_obj.pk}>")

    def batch_delete(self, queryset):
        queryset.delete()

    batch_delete.short_description = "快捷删除选中项"

    def new_list_display(self):
        new_list = []
        new_list.extend(self.list_display)
        if not self.list_display_links:
            new_list.append(ModelStark.edit)
        new_list.append(ModelStark.delete)
        new_list.insert(0, ModelStark.checkbox)
        return new_list

    def get_search_condition(self, request):
        condition = request.GET.get('tj')
        search_condition = Q()
        if condition:
            search_condition.connector = "or"
            for field in self.search_fields:
                search_condition.children.append((f"{field}__icontains", condition))
        return search_condition

    def get_filter_condition(self, request):
        condition_dict = request.GET
        filter_condition = Q()
        for condition, val in condition_dict.items():
            if condition in ['page', 'tj']:
                pass
            else:
                filter_condition.children.append((condition, val))
        return filter_condition

    def listview(self, request):

        # 批量操作
        if request.method == "POST":
            print(666)
            pk_list = request.POST.getlist('checkbox_pk')
            queryset = self.model.objects.filter(pk__in=pk_list)
            action_name = request.POST.get("action")
            try:
                action = getattr(self, action_name)
                action(queryset)
            except:
                code = 1

        # 添加数据的url，给前端添加button的
        add_url = self.get_add_url()
        # 数据库查询出当数据前表的所有数据
        data_list = self.model.objects.all()

        # 调用get_search_condition方法获取search查询条件
        search_conditions = self.get_search_condition(request)
        # 调用get_filter_condition方法获取filter的查询条件
        filter_conditions = self.get_filter_condition(request)
        # 过滤，找出符合要求的数据
        new_data_list = data_list.filter(search_conditions).filter(filter_conditions)

        # 调用视图展示类实例化来生成类对象
        listview_obj = ListView(self, request, new_data_list)

        # 调用试图类对象生成数据体的方法生成数据
        obj_list = listview_obj.create_body()

        # 分页组件实例化传参
        page_obj = Page(total_num=len(obj_list), page_num=request.GET.get("page", 1), request=request,
                        every_page_num=10)
        # 根据分页拿到的start和end切片得到所要的数据
        obj_list = obj_list[page_obj.start:page_obj.end]
        # 调用html方法得到分页的html代码片段
        page_html = page_obj.html

        return render(request, 'stark/list_view.html', locals())

    def get_model_form_class(self):
        class ModelForm(forms.ModelForm):
            class Meta:
                model = self.model
                fields = "__all__"

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                for field in iter(self.fields):
                    self.fields[field].widget.attrs.update({
                        'class': 'form-control'
                    })

        return ModelForm

    def get_new_form(self, form):
        from django.forms.models import ModelChoiceField
        for form_field in form:
            # print('-------------------->',form_field)
            # form_field.field用来从form表单中获得每个字段的类型
            if isinstance(form_field.field, ModelChoiceField):
                print(type(form_field.field))
                form_field.is_pop = True
                # form_field.name用来从form表单中获得字段的名称
                rel_model = self.model._meta.get_field(form_field.name).rel.to
                model_name = rel_model._meta.model_name
                app_label = rel_model._meta.app_label
                _url = reverse("%s_%s_add" % (app_label, model_name))
                form_field.url = _url

                form_field.pop_back_id = "id_" + form_field.name

        return form

    def addview(self, request):
        ModelFormClass = self.get_model_form_class()
        if request.method == 'POST':
            form_obj = ModelFormClass(request.POST)
            form_obj = self.get_new_form(form_obj)
            if form_obj.is_valid():
                obj = form_obj.save()
                is_pop = request.GET.get('pop')
                if is_pop:
                    text = str(obj)
                    pk = obj.pk
                    return render(request, "stark/pop.html", locals())
                else:
                    return redirect(self.get_check_url())
            return render(request, 'stark/addview.html', locals())

        form = ModelFormClass()
        form_obj = self.get_new_form(form)
        return render(request, 'stark/addview.html', locals())

    def changeview(self, request, id):
        ModelFormClass = self.get_model_form_class()
        # 获取当前要编辑的对象
        edit_obj = self.model.objects.get(pk=id)
        if request.method == "POST":
            form = ModelFormClass(data=request.POST, instance=edit_obj)
            if form.is_valid():
                form.save()  # update
                return redirect(self.get_check_url())
            return render(request, 'stark/changeview.html', locals())

        form_obj = ModelFormClass(instance=edit_obj)
        form_obj = self.get_new_form(form_obj)
        return render(request, 'stark/changeview.html', locals())

    def delview(self, request, id):
        check_url = self.get_check_url()
        self.model.objects.get(pk=id).delete()
        return redirect(check_url)

    def get_urls(self):
        model_name = self.model._meta.model_name
        app_label = self.model._meta.app_label
        temp = [
            url(r"^$", self.listview, name=f'{app_label}_{model_name}_check'),
            url(r"add/$", self.addview, name=f'{app_label}_{model_name}_add'),
            url(r"(\d+)/change/$", self.changeview, name=f'{app_label}_{model_name}_change'),
            url(r"(\d+)/delete/$", self.delview, name=f'{app_label}_{model_name}_delete'),

        ]
        return temp

    @property
    def urls(self):
        return self.get_urls(), None, None


class StarkSite(object):
    def __init__(self):
        # 定义一个字典用于存储接下来需要注册的model和对应congfig配置类
        self._registry = {}

    def register(self, model, admin_class=None):
        # 设置配置类，有自定义的就用自定义的，没有就用默认的ModelStark
        if not admin_class:
            admin_class = ModelStark
        # 以model为键，配置类实例化对象为值进行注册
        self._registry[model] = admin_class(model)

    def get_urls(self):
        temp = []

        # self._registry是以model为键，config_obj配置类实例化对象为值进行注册后的字典容器
        for model, config_obj in self._registry.items():
            # 通过模型表model的._meta方法得到动态的、注册的、model的名字和model所属的app名
            model_name = model._meta.model_name
            app_label = model._meta.app_label
            # "%s/%s/" % (app_label, model_name)字符串拼接先得到所需路径的前边部分'app/model/'
            # config_obj.urls为通过配置类对象调用配置类下的urls方法来得到相应model表的增删改查url
            temp.append(url(r"%s/%s/" % (app_label, model_name), config_obj.urls))

        return temp

    @property
    def urls(self):
        return self.get_urls(), None, None


site = StarkSite()
