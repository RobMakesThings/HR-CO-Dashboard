import client from './client';

export const listEntity = (entity, params) => client.get(`/${entity}`, { params }).then((r) => r.data);
export const getEntity = (entity, id) => client.get(`/${entity}/${id}`).then((r) => r.data);
export const createEntity = (entity, payload) => client.post(`/${entity}`, payload).then((r) => r.data);
export const updateEntity = (entity, id, payload) => client.put(`/${entity}/${id}`, payload).then((r) => r.data);
export const deleteEntity = (entity, id) => client.delete(`/${entity}/${id}`).then((r) => r.data);
export const generateEntity = (entity) => client.get(`/${entity}/generate`).then((r) => r.data);
export const bulkCreate = (entity, count) => client.post(`/${entity}/bulk`, null, { params: { count } }).then((r) => r.data);
export const exportEntity = (entity, params, format) =>
    client
        .get(`/export/${entity}`, { params: { ...params, format }, responseType: 'blob' })
        .then((r) => r.data);
export const lookup = (name) => client.get(`/lookup/${name}`).then((r) => r.data);
