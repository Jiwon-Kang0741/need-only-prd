import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import ConfirmationService from 'primevue/confirmationservice'
import router from './router'
import App from './App.vue'
import 'primevue/resources/themes/lara-light-blue/theme.css'
import 'primevue/resources/primevue.min.css'
import 'primeicons/primeicons.css'

// PrimeVue components — globally registered so generated code works without explicit imports
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Dropdown from 'primevue/dropdown'
import MultiSelect from 'primevue/multiselect'
import Calendar from 'primevue/calendar'
import Dialog from 'primevue/dialog'
import Toast from 'primevue/toast'
import Textarea from 'primevue/textarea'
import Checkbox from 'primevue/checkbox'
import RadioButton from 'primevue/radiobutton'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import ProgressBar from 'primevue/progressbar'
import Tag from 'primevue/tag'
import Toolbar from 'primevue/toolbar'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(PrimeVue)
app.use(ToastService)
app.use(ConfirmationService)

// Register globally
app.component('DataTable', DataTable)
app.component('Column', Column)
app.component('Button', Button)
app.component('InputText', InputText)
app.component('InputNumber', InputNumber)
app.component('Dropdown', Dropdown)
app.component('MultiSelect', MultiSelect)
app.component('Calendar', Calendar)
app.component('Dialog', Dialog)
app.component('Toast', Toast)
app.component('Textarea', Textarea)
app.component('Checkbox', Checkbox)
app.component('RadioButton', RadioButton)
app.component('TabView', TabView)
app.component('TabPanel', TabPanel)
app.component('ProgressBar', ProgressBar)
app.component('Tag', Tag)
app.component('Toolbar', Toolbar)

app.mount('#app')
