
const API = 'http://localhost:5000/api';

const { createApp } = Vue;

createApp({
    data() {
        return {
            page: 'login',
            currentUser: null,
            token: null,
            alert: { message: '', type: 'info' },
            loginForm: { email: '', password: '' },
            regStudent: { username: '', email: '', password: '', full_name: '', roll_number: '', degree: '', branch: '', cgpa: '', skills: '' },
            regCompany: { username: '', email: '', password: '', company_name: '', industry: '', location: '', hr_contact: '', website: '', description: '' },
            driveForm: { job_title: '', job_description: '', eligibility_criteria: '', required_skills: '', salary_range: '', application_deadline: '' },
            profileForm: { full_name: '', degree: '', branch: '', cgpa: '', skills: '' },
            // Admin data
            adminStats: [],
            pendingCompanies: [],
            pendingDrives: [],
            companiesList: [],
            studentsList: [],
            drivesList: [],
            companySearch: '',
            studentSearch: '',
            adminApplicationsList: [],
            adminPlacementsList: [],
            // Company data
            companyData: {},
            companyDrives: [],
            applicationsList: [],
            currentDriveId: null,
            // Student data
            studentData: {},
            studentApplications: [],
            availableDrives: [],
            placementsList: [],
            driveSearch: '',
        }
    },
    computed: {
        roleBadge() {
            if (!this.currentUser) return '';
            const badges = { admin: 'bg-danger', company: 'bg-warning text-dark', student: 'bg-success' };
            return 'badge ' + (badges[this.currentUser.role] || 'bg-secondary');
        }
    },
    methods: {
        showAlert(message, type='success') {
            this.alert = { message, type };
            setTimeout(() => this.alert.message = '', 4000);
        },
        authHeaders() {
            return { Authorization: `Bearer ${this.token}` };
        },
        async login() {
            try {
                const res = await axios.post(`${API}/auth/login`, this.loginForm);
                this.token = res.data.token;
                this.currentUser = { role: res.data.role };
                localStorage.setItem('token', this.token);
                localStorage.setItem('role', res.data.role);
                await this.fetchMe();
                this.page = 'dashboard';
                await this.loadDashboard();
            } catch(e) {
                this.showAlert(e.response?.data?.error || 'Login failed', 'danger');
            }
        },
        async fetchMe() {
            const res = await axios.get(`${API}/auth/me`, { headers: this.authHeaders() });
            this.currentUser = res.data;
        },
        async registerStudent() {
            if (!this.regStudent.username || !this.regStudent.email || 
                !this.regStudent.password || !this.regStudent.full_name || 
                !this.regStudent.roll_number) {
                this.showAlert('Please fill all required fields', 'danger');
                return;
                }
            try {
                const formData = new FormData();
                Object.keys(this.regStudent).forEach(k => formData.append(k, this.regStudent[k]));
                if (this.$refs.regResumeFile?.files[0]) {
                    formData.append('resume', this.$refs.regResumeFile.files[0]);
                }
                await axios.post(`${API}/auth/register/student`, formData, {
                    headers: { 'Content-Type': 'multipart/form-data' }
                });
                this.showAlert('Registration successful! You can now log in.');
                this.page = 'login';
            } catch(e) {
                this.showAlert(e.response?.data?.error || 'Registration failed', 'danger');
            }
        },
        async registerCompany() {
            try {
                await axios.post(`${API}/auth/register/company`, this.regCompany);
                this.showAlert('Registration submitted! Await admin approval.');
                this.page = 'login';
            } catch(e) {
                this.showAlert(e.response?.data?.error || 'Registration failed', 'danger');
            }
        },
        logout() {
            this.token = null;
            this.currentUser = null;
            localStorage.removeItem('token');
            localStorage.removeItem('role');
            this.page = 'login';
        },
        async navigateTo(page) {
            this.page = page;
            if (page === 'companies') await this.searchCompanies();
            else if (page === 'students') await this.searchStudents();
            else if (page === 'drives') await this.loadDrives();
            else if (page === 'applications-admin') await this.loadAdminApplications();
            else if (page === 'placements-admin') await this.loadAdminPlacements();
        },
        async loadDashboard() {
            const role = this.currentUser.role;
            if (role === 'admin') await this.loadAdminDashboard();
            else if (role === 'company') await this.loadCompanyDashboard();
            else if (role === 'student') await this.loadStudentDashboard();
        },
        // ── ADMIN ──
        async loadAdminDashboard() {
            const res = await axios.get(`${API}/admin/dashboard`, { headers: this.authHeaders() });
            const d = res.data;
            this.pendingCompanies = d.pending_companies;
            this.pendingDrives = d.pending_drives;
            this.adminStats = [
                { label: 'Companies', value: d.total_companies, icon: 'bi-building', color: '#ffa726', page: 'companies', action: 'Manage' },
                { label: 'Students', value: d.total_students, icon: 'bi-people-fill', color: '#4fc3f7', page: 'students', action: 'Manage' },
                { label: 'Drives', value: d.total_drives, icon: 'bi-briefcase-fill', color: '#66bb6a', page: 'drives', action: 'Manage' },
                { label: 'Applications', value: d.total_applications, icon: 'bi-file-earmark-text-fill', color: '#ef5350', page: 'applications-admin', action: 'View' },
                { label: 'Placements', value: d.total_placements, icon: 'bi-trophy-fill', color: '#ab47bc', page: 'placements-admin', action: 'View' },
            ];
        },
        async loadAdminApplications() {
            const res = await axios.get(`${API}/admin/applications`, { headers: this.authHeaders() });
            this.adminApplicationsList = res.data;
        },
        async loadAdminPlacements() {
            const res = await axios.get(`${API}/admin/placements`, { headers: this.authHeaders() });
            this.adminPlacementsList = res.data;
        },
        async searchCompanies() {
            const res = await axios.get(`${API}/admin/companies?search=${this.companySearch}`, { headers: this.authHeaders() });
            this.companiesList = res.data;
            this.page = 'companies';
        },
        async searchStudents() {
            const res = await axios.get(`${API}/admin/students?search=${this.studentSearch}`, { headers: this.authHeaders() });
            this.studentsList = res.data;
            this.page = 'students';
        },
        async loadDrives() {
            const res = await axios.get(`${API}/admin/drives`, { headers: this.authHeaders() });
            this.drivesList = res.data;
            this.page = 'drives';
        },
        async approveCompany(id) {
            await axios.post(`${API}/admin/company/${id}/approve`, {}, { headers: this.authHeaders() });
            this.showAlert('Company approved');
            await this.loadAdminDashboard();
            if (this.page === 'companies') await this.searchCompanies();
        },
        async rejectCompany(id) {
            await axios.post(`${API}/admin/company/${id}/reject`, {}, { headers: this.authHeaders() });
            this.showAlert('Company rejected', 'warning');
            await this.loadAdminDashboard();
        },
        async blacklistCompany(id) {
            await axios.post(`${API}/admin/company/${id}/blacklist`, {}, { headers: this.authHeaders() });
            this.showAlert('Company blacklist status toggled', 'warning');
            await this.searchCompanies();
        },
        async deleteCompany(id) {
            if (!confirm('Delete this company?')) return;
            await axios.delete(`${API}/admin/company/${id}/delete`, { headers: this.authHeaders() });
            this.showAlert('Company deleted', 'danger');
            await this.searchCompanies();
            await this.loadAdminDashboard(); 
        },
        async blacklistStudent(id) {
            await axios.post(`${API}/admin/student/${id}/blacklist`, {}, { headers: this.authHeaders() });
            this.showAlert('Student blacklist status toggled', 'warning');
            await this.searchStudents();
            await this.loadAdminDashboard(); 
        },
        async deleteStudent(id) {
            if (!confirm('Delete this student?')) return;
            await axios.delete(`${API}/admin/student/${id}/delete`, { headers: this.authHeaders() });
            this.showAlert('Student deleted', 'danger');
            await this.searchStudents();
        },
        async approveDrive(id) {
            await axios.post(`${API}/admin/drive/${id}/approve`, {}, { headers: this.authHeaders() });
            this.showAlert('Drive approved');
            await this.loadAdminDashboard();
            if (this.page === 'drives') await this.loadDrives();
        },
        async rejectDrive(id) {
            await axios.post(`${API}/admin/drive/${id}/reject`, {}, { headers: this.authHeaders() });
            this.showAlert('Drive rejected', 'warning');
            await this.loadAdminDashboard();
        },
        // ── COMPANY ──
        async loadCompanyDashboard() {
            const res = await axios.get(`${API}/company/dashboard`, { headers: this.authHeaders() });
            this.companyData = res.data.company;
            this.companyDrives = res.data.drives;
        },
        async createDrive() {
            try {
                await axios.post(`${API}/company/drive`, this.driveForm, { headers: this.authHeaders() });
                this.showAlert('Drive created! Awaiting admin approval.');
                this.page = 'dashboard';
                await this.loadCompanyDashboard();
            } catch(e) {
                this.showAlert(e.response?.data?.error || 'Failed to create drive', 'danger');
            }
        },
        async closeDrive(id) {
            await axios.post(`${API}/company/drive/${id}/close`, {}, { headers: this.authHeaders() });
            this.showAlert('Drive closed', 'warning');
            await this.loadCompanyDashboard();
        },
        async deleteDrive(id) {
            if (!confirm('Delete this drive?')) return;
            await axios.delete(`${API}/company/drive/${id}/delete`, { headers: this.authHeaders() });
            this.showAlert('Drive deleted', 'danger');
            await this.loadCompanyDashboard();
        },
        async viewApplications(driveId) {
            this.currentDriveId = driveId;
            const res = await axios.get(`${API}/company/drive/${driveId}/applications`, { headers: this.authHeaders() });
            this.applicationsList = res.data.map(a => ({ ...a, newStatus: a.status, salary: '' }));
            this.page = 'applications';
        },
        async updateApplication(app) {
            try {
                await axios.put(`${API}/company/application/${app.id}`, {
                    status: app.newStatus,
                    salary: app.salary,
                    note: app.note
                }, { headers: this.authHeaders() });
                this.showAlert('Application updated');
                await this.viewApplications(this.currentDriveId);
            } catch(e) {
                this.showAlert(e.response?.data?.error || 'Update failed', 'danger');
            }
        },
        // ── STUDENT ──
        async loadStudentDashboard() {
            const res = await axios.get(`${API}/student/dashboard`, { headers: this.authHeaders() });
            this.studentData = res.data.student;
            this.availableDrives = res.data.drives;
            this.studentApplications = res.data.applications;
        },
        async uploadResume(event) {
            const file = event.target.files[0];
            if (!file) return;
            const formData = new FormData();
            formData.append('resume', file);
            try {
                await axios.post(`${API}/student/profile/resume`, formData, {
                    headers: { ...this.authHeaders(), 'Content-Type': 'multipart/form-data' }
                });
                this.showAlert('Resume uploaded!');
                await this.loadStudentDashboard();
            } catch(e) {
                this.showAlert(e.response?.data?.error || 'Upload failed', 'danger');
            }
        },
        async searchDrives() {
            const res = await axios.get(`${API}/student/dashboard?search=${this.driveSearch}`, { headers: this.authHeaders() });
            this.availableDrives = res.data.drives;
        },
        async applyDrive(id) {
            try {
                await axios.post(`${API}/student/apply/${id}`, {}, { headers: this.authHeaders() });
                this.showAlert('Applied successfully!');
                await this.loadStudentDashboard();
            } catch(e) {
                this.showAlert(e.response?.data?.error || 'Apply failed', 'danger');
            }
        },
        async loadPlacements() {
            const res = await axios.get(`${API}/student/placements`, { headers: this.authHeaders() });
            this.placementsList = res.data;
            this.page = 'placements';
        },
        async saveProfile() {
            try {
                await axios.put(`${API}/student/profile`, this.profileForm, { headers: this.authHeaders() });
                this.showAlert('Profile updated!');
                await this.loadStudentDashboard();
                this.page = 'dashboard';
            } catch(e) {
                this.showAlert('Update failed', 'danger');
            }
        },
        async exportCSV(role) {
            try {
                const endpoint = role === 'student' ? `${API}/student/export` : `${API}/company/export`;
                await axios.post(endpoint, {}, { headers: this.authHeaders() });
                this.showAlert('Export started! Check backend/static/exports/ folder.');
            } catch(e) {
                this.showAlert('Export failed', 'danger');
            }
        },
        driveStatusBadge(status) {
            const map = { Approved: 'badge bg-success', Pending: 'badge bg-warning text-dark', Rejected: 'badge bg-danger', Closed: 'badge bg-secondary' };
            return map[status] || 'badge bg-secondary';
        },
        appStatusBadge(status) {
            const map = { Applied: 'badge bg-secondary', Shortlisted: 'badge bg-info', Interview: 'badge bg-primary', Selected: 'badge bg-success', Rejected: 'badge bg-danger' };
            return map[status] || 'badge bg-secondary';
        },
    },
    async mounted() {
        const token = localStorage.getItem('token');
        const role = localStorage.getItem('role');
        if (token && role) {
            this.token = token;
            this.currentUser = { role };
            try {
                await this.fetchMe();
                this.page = 'dashboard';
                await this.loadDashboard();
            } catch(e) {
                this.logout();
            }
        }
    }
}).mount('#app');