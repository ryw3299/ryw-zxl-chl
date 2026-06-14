{
  path: '/admin',
  component: () => import('@/components/PageLayout.vue'),
  meta: { requiresAuth: true, roles: ['admin'] },
  children: [
    { path: '', name: 'Admin', component: () => import('@/views/AdminPage.vue') },
  ],
},
